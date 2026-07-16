from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ipware import get_client_ip

from .models import Website, SocialConnection, ScrapeResult, SampleContent
from .serializers import WebsiteSerializer, SocialConnectionSerializer, ScrapeResultSerializer, SampleContentSerializer
from .tasks import crawl_website_task
from logs.models import ActivityLog
from accounts.permissions import IsAdminOrSuperAdmin, IsSuperAdmin


class WebsiteListCreateView(generics.ListCreateAPIView):
    serializer_class = WebsiteSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        show_deleted = self.request.query_params.get('trash') == 'true'
        # Super admin sees all; admin sees only their own
        if user.role == 'super_admin':
            qs = Website.objects.all().prefetch_related('social_connections')
        else:
            qs = Website.objects.filter(owner=user).prefetch_related('social_connections')
        return qs.filter(is_deleted=show_deleted)

    def perform_create(self, serializer):
        ip, _ = get_client_ip(self.request)
        has_samples = self.request.data.get('has_samples', False)
        scrape_status = 'done' if has_samples else 'pending'
        needs_crawl = not has_samples

        website = serializer.save(
            owner=self.request.user,
            scrape_status=scrape_status,
            needs_crawl=needs_crawl
        )
        ActivityLog.objects.create(
            actor=self.request.user, actor_name=self.request.user.get_full_name(),
            action='website_add', target_description=website.name,
            ip_address=ip
        )


class WebsiteDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WebsiteSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Website.objects.all()
        return Website.objects.filter(owner=user)

    def perform_update(self, serializer):
        instance = self.get_object()
        old_data = {
            'name': instance.name,
            'domain': instance.domain,
            'url': instance.url,
            'industry': instance.industry,
            'tone': instance.tone,
            'topics': instance.topics,
            'status': instance.status,
        }
        website = serializer.save()
        new_data = {
            'name': website.name,
            'domain': website.domain,
            'url': website.url,
            'industry': website.industry,
            'tone': website.tone,
            'topics': website.topics,
            'status': website.status,
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
                action='website_update',
                target_description=website.name,
                ip_address=ip,
                metadata={'changes': changes}
            )

    def perform_destroy(self, instance):
        ip, _ = get_client_ip(self.request)
        hard = self.request.query_params.get('hard') == 'true'
        ActivityLog.objects.create(
            actor=self.request.user,
            actor_name=self.request.user.get_full_name(),
            action='website_delete_permanent' if hard else 'website_delete',
            target_description=instance.name,
            ip_address=ip
        )
        if hard:
            instance.delete()
        else:
            instance.is_deleted = True
            instance.save(update_fields=['is_deleted'])


class TriggerCrawlView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        try:
            website = Website.objects.get(pk=pk)
        except Website.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)
        
        website.scrape_status = 'crawling'
        website.save(update_fields=['scrape_status'])
        
        # Fire async Celery task safely
        from content.views import run_task_async
        run_task_async(crawl_website_task, pk)
        
        ip, _ = get_client_ip(request)
        ActivityLog.objects.create(
            actor=request.user, actor_name=request.user.get_full_name(),
            action='crawl_start', target_description=website.name,
            ip_address=ip
        )
        return Response({'status': 'crawling', 'website_id': pk})


class CrawlStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            website = Website.objects.get(pk=pk)
        except Website.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)
        return Response({
            'status': website.scrape_status,
            'last_crawled': website.last_crawled,
            'scrape_summary': website.scrape_summary,
        })


class SocialConnectionView(generics.ListCreateAPIView):
    serializer_class = SocialConnectionSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        return SocialConnection.objects.filter(website_id=self.kwargs['pk'])

    def perform_create(self, serializer):
        website = Website.objects.get(pk=self.kwargs['pk'])
        platform = serializer.validated_data.get('platform')
        existing = SocialConnection.objects.filter(website=website, platform=platform).first()
        if existing:
            serializer.instance = existing
            conn = serializer.save(is_active=True)
        else:
            conn = serializer.save(website=website)
        ActivityLog.objects.create(
            actor=self.request.user, actor_name=self.request.user.get_full_name(),
            action='social_connected',
            target_description=f"{website.name} → {conn.platform}"
        )


class SocialConnectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SocialConnectionSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = SocialConnection.objects.all()
    lookup_url_kwarg = 'conn_pk'

class WebsiteStatsView(APIView):
    """Returns published/scheduled/pending counts for dashboard cards."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from content.models import ContentDraft, ScheduledPost
        from django.utils import timezone
        from datetime import timedelta
        
        # Verify website exists and is owned by the user
        try:
            if request.user.role == 'super_admin':
                website = Website.objects.get(pk=pk)
            else:
                website = Website.objects.get(pk=pk, owner=request.user)
        except Website.DoesNotExist:
            return Response({'detail': 'Website not found.'}, status=404)
            
        drafts = ContentDraft.objects.filter(website=website)
        
        # Calculate current week boundaries (Monday to Sunday)
        now = timezone.now()
        start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)
        
        scheduled_count = ScheduledPost.objects.filter(
            draft__website=website,
            scheduled_for__range=(start_of_week, end_of_week)
        ).count()
        
        return Response({
            'published': drafts.filter(status='published').count(),
            'scheduled': scheduled_count,
            'pending': drafts.filter(status='draft').count(),
            'approved': drafts.filter(status='approved').count(),
            'rejected': drafts.filter(status='rejected').count(),
            'pages': ScrapeResult.objects.filter(website=website).count(),
        })


class WebsitePagesListView(generics.ListAPIView):
    """Returns crawled pages for onboarding preview."""
    serializer_class = ScrapeResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        pk = self.kwargs['pk']
        try:
            if user.role == 'super_admin':
                website = Website.objects.get(pk=pk)
            else:
                website = Website.objects.get(pk=pk, owner=user)
        except Website.DoesNotExist:
            return ScrapeResult.objects.none()
        return ScrapeResult.objects.filter(website=website)


class SampleContentView(generics.ListCreateAPIView):
    """List and create samples for a website."""
    serializer_class = SampleContentSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    
    def get_queryset(self):
        user = self.request.user
        pk = self.kwargs['pk']
        try:
            if user.role == 'super_admin':
                website = Website.objects.get(pk=pk)
            else:
                website = Website.objects.get(pk=pk, owner=user)
        except Website.DoesNotExist:
            return SampleContent.objects.none()
        return SampleContent.objects.filter(website=website)
    
    def perform_create(self, serializer):
        user = self.request.user
        pk = self.kwargs['pk']
        try:
            if user.role == 'super_admin':
                website = Website.objects.get(pk=pk)
            else:
                website = Website.objects.get(pk=pk, owner=user)
        except Website.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Website not found.')
            
        instance = serializer.save(website=website)
        
        website.scrape_status = 'done'
        website.needs_crawl = False
        website.save(update_fields=['scrape_status', 'needs_crawl'])
        
        ip, _ = get_client_ip(self.request)
        
        # Log activity
        ActivityLog.objects.create(
            actor=self.request.user,
            actor_name=self.request.user.get_full_name(),
            action='samples_uploaded',
            target_description=f"Uploaded {instance.platform} sample for {website.name}",
            ip_address=ip
        )


class SampleContentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a sample."""
    serializer_class = SampleContentSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    lookup_url_kwarg = 'sample_pk'
    
    def get_queryset(self):
        user = self.request.user
        qs = SampleContent.objects.all()
        if user.role != 'super_admin':
            qs = qs.filter(website__owner=user)
        return qs


class TestConnectionView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk, platform):
        url = request.data.get('make_webhook_url', '')
        auth_type = request.data.get('auth_type', 'none')
        auth_payload_raw = request.data.get('auth_payload_write', {})

        if not url:
            return Response({'connected': False, 'detail': 'URL is required'}, status=400)

        # Restore password/token if placeholder is passed
        if any(v == "••••••••" for v in auth_payload_raw.values()):
            try:
                conn = SocialConnection.objects.filter(website_id=pk, platform=platform).first()
                if conn and conn.auth_payload:
                    from websites.utils import decrypt_value
                    import json
                    existing_payload = json.loads(decrypt_value(conn.auth_payload))
                    for k, v in auth_payload_raw.items():
                        if v == "••••••••" and k in existing_payload:
                            auth_payload_raw[k] = existing_payload[k]
            except Exception:
                pass

        # Call backend test connection helper
        from websites.utils import test_connection_helper
        success = test_connection_helper(platform, url, auth_type, auth_payload_raw)

        return Response({'connected': success})