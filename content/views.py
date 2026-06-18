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


class ContentDraftListView(generics.ListAPIView):
    serializer_class = ContentDraftSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ContentDraft.objects.select_related('website', 'reviewed_by')
        # Filters
        website_id = self.request.query_params.get('website')
        draft_status = self.request.query_params.get('status')
        platform = self.request.query_params.get('platform')
        if website_id:
            qs = qs.filter(website_id=website_id)
        if draft_status:
            qs = qs.filter(status=draft_status)
        if platform:
            qs = qs.filter(platform=platform)
        return qs


class ContentDraftDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ContentDraftSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = ContentDraft.objects.all()

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
        draft.status = 'draft'
        draft.body = ''
        draft.save()
        regenerate_draft_task.delay(pk)
        ip, _ = get_client_ip(request)
        ActivityLog.objects.create(
            actor=request.user, actor_name=request.user.get_full_name(),
            action='content_regenerated', target_description=draft.title,
            ip_address=ip,
            metadata={'changes': {'status': {'old': old_status, 'new': 'draft'}}}
        )
        return Response({'status': 'regenerating', 'draft_id': pk})


class ScheduleDraftView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        draft = ContentDraft.objects.get(pk=pk)
        if draft.status != 'approved':
            return Response({'detail': 'Draft must be approved first.'}, status=400)
        
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