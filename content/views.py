from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from ipware import get_client_ip

from .models import ContentIdea, ContentDraft, ScheduledPost
from .serializers import (ContentIdeaSerializer, ContentDraftSerializer,
                           ScheduledPostSerializer)
from .tasks import generate_content_task, regenerate_draft_task
from .generator import generate_idea_suggestions

from logs.models import ActivityLog
from accounts.permissions import IsAdminOrSuperAdmin


class ContentIdeaListCreateView(generics.ListCreateAPIView):
    serializer_class = ContentIdeaSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        qs = ContentIdea.objects.select_related('website', 'submitted_by')
        website_id = self.request.query_params.get('website')
        if website_id:
            qs = qs.filter(website_id=website_id)
        return qs

    def perform_create(self, serializer):
        ip, _ = get_client_ip(self.request)
        idea = serializer.save(submitted_by=self.request.user)
        ActivityLog.objects.create(
            actor=self.request.user, actor_name=self.request.user.get_full_name(),
            action='content_idea_submit',
            target_description=f"{idea.title} for {idea.website.name}",
            ip_address=ip
        )


class ContentIdeaDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContentIdeaSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = ContentIdea.objects.all()


class GenerateContentView(APIView):
    """Triggers AI generation for a given idea."""
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        try:
            idea = ContentIdea.objects.get(pk=pk)
        except ContentIdea.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)
        
        idea.status = 'generating'
        idea.save(update_fields=['status'])
        generate_content_task.delay(pk)
        return Response({'status': 'generating', 'idea_id': pk})


class ContentDraftListView(generics.ListCreateAPIView):
    serializer_class = ContentDraftSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ContentDraft.objects.select_related('website', 'reviewed_by')
        # Filters
        website_id = self.request.query_params.get('website')
        draft_status = self.request.query_params.get('status')
        platform = self.request.query_params.get('platform')
        show_deleted = self.request.query_params.get('trash') == 'true'
        if website_id:
            qs = qs.filter(website_id=website_id)
        if draft_status:
            qs = qs.filter(status=draft_status)
        if platform:
            qs = qs.filter(platform=platform)
        return qs.filter(is_deleted=show_deleted)


class ContentDraftDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContentDraftSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = ContentDraft.objects.all()

    def perform_destroy(self, instance):
        ip, _ = get_client_ip(self.request)
        hard = self.request.query_params.get('hard') == 'true'
        ActivityLog.objects.create(
            actor=self.request.user,
            actor_name=self.request.user.get_full_name(),
            action='content_delete_permanent' if hard else 'content_delete',
            target_description=instance.title,
            ip_address=ip
        )
        if hard:
            instance.delete()
        else:
            instance.is_deleted = True
            instance.save(update_fields=['is_deleted'])

    def perform_update(self, serializer):
        instance = self.get_object()
        old_data = {
            'title': instance.title,
            'body': instance.body,
            'status': instance.status,
            'excerpt': instance.excerpt,
            'category': instance.category,
        }
        draft = serializer.save()
        new_data = {
            'title': draft.title,
            'body': draft.body,
            'status': draft.status,
            'excerpt': draft.excerpt,
            'category': draft.category,
        }
        ip, _ = get_client_ip(self.request)
        changes = {}
        for key, new_val in new_data.items():
            old_val = old_data.get(key)
            if old_val != new_val:
                changes[key] = {
                    'old': old_val,
                    'new': new_val
                }
        if changes:
            ActivityLog.objects.create(
                actor=self.request.user,
                actor_name=self.request.user.get_full_name(),
                action='content_update',
                target_description=draft.title,
                ip_address=ip,
                metadata={'changes': changes}
            )


class ApproveDraftView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        draft = ContentDraft.objects.get(pk=pk)
        old_status = draft.status
        draft.status = 'approved'
        draft.reviewed_by = request.user
        draft.reviewed_at = timezone.now()
        draft.save()
        ip, _ = get_client_ip(request)
        ActivityLog.objects.create(
            actor=request.user, actor_name=request.user.get_full_name(),
            action='content_approved', target_description=draft.title,
            ip_address=ip,
            metadata={'changes': {'status': {'old': old_status, 'new': 'approved'}}}
        )
        return Response(ContentDraftSerializer(draft).data)


class RejectDraftView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        draft = ContentDraft.objects.get(pk=pk)
        old_status = draft.status
        draft.status = 'rejected'
        draft.reviewed_by = request.user
        draft.reviewed_at = timezone.now()
        draft.rejection_reason = request.data.get('reason', '')
        draft.save()
        ip, _ = get_client_ip(request)
        ActivityLog.objects.create(
            actor=request.user, actor_name=request.user.get_full_name(),
            action='content_rejected', target_description=draft.title,
            ip_address=ip,
            metadata={'changes': {
                'status': {'old': old_status, 'new': 'rejected'},
                'rejection_reason': {'old': '', 'new': draft.rejection_reason}
            }}
        )
        return Response(ContentDraftSerializer(draft).data)


class RegenerateDraftView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        draft = ContentDraft.objects.get(pk=pk)
        old_status = draft.status
        regenerate_type = request.data.get('type', 'all')
        
        if regenerate_type in ['all', 'content']:
            draft.status = 'draft'
            draft.body = ''
            draft.save()
        
        idea_id = draft.idea_id if draft.idea else None
        
        regenerate_draft_task.delay(pk, regenerate_type=regenerate_type)
        
        new_draft_id = pk
        if idea_id and regenerate_type in ['all', 'content']:
            new_draft = ContentDraft.objects.filter(idea_id=idea_id).order_by('-id').first()
            if new_draft:
                new_draft_id = new_draft.id
                
        ip, _ = get_client_ip(request)
        action_name = 'content_regenerated'
        if regenerate_type == 'image':
            action_name = 'image_regenerated'
        elif regenerate_type == 'content':
            action_name = 'content_text_regenerated'
            
        ActivityLog.objects.create(
            actor=request.user, actor_name=request.user.get_full_name(),
            action=action_name, target_description=draft.title,
            ip_address=ip,
            metadata={'changes': {'status': {'old': old_status, 'new': 'draft'}}}
        )
        return Response({'status': 'regenerating', 'draft_id': pk, 'new_draft_id': new_draft_id})


class ScheduleDraftView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        draft = ContentDraft.objects.get(pk=pk)
        if draft.status not in ['draft', 'approved', 'scheduled']:
            return Response({'detail': 'Draft must be in draft, approved, or scheduled status first.'}, status=400)
        
        scheduled_for = request.data.get('scheduled_for')
        if not scheduled_for:
            return Response({'detail': 'scheduled_for is required.'}, status=400)
        
        sp, created = ScheduledPost.objects.update_or_create(
            draft=draft,
            defaults={'scheduled_for': scheduled_for}
        )
        old_status = draft.status
        draft.status = 'scheduled'
        draft.save()
        ip, _ = get_client_ip(request)
        ActivityLog.objects.create(
            actor=request.user, actor_name=request.user.get_full_name(),
            action='content_scheduled',
            target_description=f"{draft.title} @ {scheduled_for}",
            ip_address=ip,
            metadata={'changes': {
                'status': {'old': old_status, 'new': 'scheduled'},
                'scheduled_for': {'old': None, 'new': scheduled_for}
            }}
        )
        return Response(ScheduledPostSerializer(sp).data)


class ScheduledPostListView(generics.ListAPIView):
    serializer_class = ScheduledPostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ScheduledPost.objects.select_related('draft__website')
        website_id = self.request.query_params.get('website')
        if website_id:
            qs = qs.filter(draft__website_id=website_id)
        return qs


class ApprovalsQueueView(generics.ListAPIView):
    """Cross-website pending drafts for the approvals page."""
    serializer_class = ContentDraftSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = ContentDraft.objects.filter(status='draft').select_related('website')
        if user.role != 'super_admin':
            qs = qs.filter(website__owner=user)
        return qs


class UnscheduleDraftView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        try:
            draft = ContentDraft.objects.get(pk=pk)
        except ContentDraft.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)

        if draft.status == 'scheduled':
            ScheduledPost.objects.filter(draft=draft).delete()
            old_status = draft.status
            draft.status = 'approved'
            draft.save(update_fields=['status'])
            ip, _ = get_client_ip(request)
            ActivityLog.objects.create(
                actor=request.user, actor_name=request.user.get_full_name(),
                action='content_unscheduled',
                target_description=draft.title,
                ip_address=ip,
                metadata={'changes': {
                    'status': {'old': old_status, 'new': 'approved'}
                }}
            )
            return Response({'status': 'approved'})
        return Response({'detail': 'Draft is not scheduled.'}, status=400)


class IdeaSuggestionsView(APIView):
    """
    Generates dynamic AI-powered content idea suggestions for a website.
    Uses the website's industry, topics, and scrape_summary plus a live trend
    search to return 8 timely, brand-relevant content ideas.

    POST /api/content/suggestions/?website=<id>
    Returns: [{"title": str, "platform": str, "reason": str}, ...]
    """
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request):
        from websites.models import Website
        website_id = request.query_params.get('website') or request.data.get('website')
        if not website_id:
            return Response({'detail': 'website query param is required.'}, status=400)
        try:
            website = Website.objects.get(pk=website_id)
        except Website.DoesNotExist:
            return Response({'detail': 'Website not found.'}, status=404)

        suggestions = generate_idea_suggestions(website)
        return Response(suggestions)


class InjectInternalLinksView(APIView):
    """
    Manually triggers the internal linking processor on a draft blog post,
    scanning other published articles and wrapping matching keywords in <a> tags.
    """
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        try:
            draft = ContentDraft.objects.get(pk=pk)
        except ContentDraft.DoesNotExist:
            return Response({'detail': 'Draft not found.'}, status=404)
            
        if draft.platform != 'blog':
            return Response({'detail': 'Internal links can only be injected into blog posts.'}, status=400)
            
        from .utils import inject_internal_links
        inject_internal_links(draft)
        
        return Response(ContentDraftSerializer(draft).data)


class RemoveInternalLinksView(APIView):
    """
    Strips all <a> tags from the draft blog post body, keeping the anchor text intact,
    and saving the cleaned body back to the database.
    """
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        try:
            draft = ContentDraft.objects.get(pk=pk)
        except ContentDraft.DoesNotExist:
            return Response({'detail': 'Draft not found.'}, status=404)
            
        if draft.platform != 'blog':
            return Response({'detail': 'Only blog drafts can have links removed.'}, status=400)
            
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(draft.body or '', 'html.parser')
        for a in soup.find_all('a'):
            a.unwrap()
        
        draft.body = str(soup)
        draft.save(update_fields=['body'])
        
        return Response(ContentDraftSerializer(draft).data)


class TokenUsageStatsView(APIView):
    """
    Returns aggregated token and cost usage statistics for a specific website.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from .models import TokenUsage
        from django.db.models import Sum
        from datetime import timedelta
        
        # Verify website exists
        from websites.models import Website
        try:
            website = Website.objects.get(pk=pk)
        except Website.DoesNotExist:
            return Response({'detail': 'Website not found.'}, status=404)
            
        usages = TokenUsage.objects.filter(website_id=pk)
        
        # Aggregates
        totals = usages.aggregate(
            total_tokens=Sum('total_tokens'),
            prompt_tokens=Sum('prompt_tokens'),
            completion_tokens=Sum('completion_tokens'),
            total_cost=Sum('cost')
        )
        
        total_tokens = totals.get('total_tokens') or 0
        prompt_tokens = totals.get('prompt_tokens') or 0
        completion_tokens = totals.get('completion_tokens') or 0
        total_cost = float(totals.get('total_cost') or 0.0)
        
        # Weekly trend (last 7 days)
        weekly_history = []
        today = timezone.now().date()
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_start = timezone.datetime.combine(day, timezone.datetime.min.time())
            day_end = timezone.datetime.combine(day, timezone.datetime.max.time())
            # Make aware if timezone support is active
            if timezone.is_aware(timezone.now()):
                day_start = timezone.make_aware(day_start)
                day_end = timezone.make_aware(day_end)
            
            day_total = usages.filter(created_at__range=(day_start, day_end)).aggregate(Sum('total_tokens')).get('total_tokens__sum') or 0
            weekly_history.append({
                'day': day.strftime('%a'),
                'date': day.strftime('%Y-%m-%d'),
                'tokens': day_total
            })
            
        # Model breakdown
        model_breakdown = {}
        for usage in usages.values('model_name').annotate(total=Sum('total_tokens'), cost=Sum('cost')):
            model_breakdown[usage['model_name']] = {
                'tokens': usage['total'] or 0,
                'cost': float(usage['cost'] or 0.0)
            }
            
        # Section breakdown
        section_breakdown = {}
        for usage in usages.values('section').annotate(total=Sum('total_tokens'), cost=Sum('cost')):
            label = dict(TokenUsage.SECTION_CHOICES).get(usage['section'], usage['section'])
            section_breakdown[label] = {
                'tokens': usage['total'] or 0,
                'cost': float(usage['cost'] or 0.0)
            }
            
        return Response({
            'total_tokens': total_tokens,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_cost': total_cost,
            'weekly_history': weekly_history,
            'model_breakdown': model_breakdown,
            'section_breakdown': section_breakdown
        })