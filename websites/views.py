from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ipware import get_client_ip

from .models import Website, SocialConnection, ScrapeResult
from .serializers import WebsiteSerializer, SocialConnectionSerializer, ScrapeResultSerializer
from .tasks import crawl_website_task
from logs.models import ActivityLog
from accounts.permissions import IsAdminOrSuperAdmin, IsSuperAdmin


class WebsiteListCreateView(generics.ListCreateAPIView):
    serializer_class = WebsiteSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        # Super admin sees all; admin sees only their own
        if user.role == 'super_admin':
            return Website.objects.all().prefetch_related('social_connections')
        return Website.objects.filter(owner=user).prefetch_related('social_connections')

    def perform_create(self, serializer):
        ip, _ = get_client_ip(self.request)
        website = serializer.save(owner=self.request.user)
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
        ActivityLog.objects.create(
            actor=self.request.user,
            actor_name=self.request.user.get_full_name(),
            action='website_delete',
            target_description=instance.name,
            ip_address=ip
        )
        instance.delete()


class TriggerCrawlView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        try:
            website = Website.objects.get(pk=pk)
        except Website.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)
        
        website.scrape_status = 'crawling'
        website.save(update_fields=['scrape_status'])
        
        # Fire async Celery task
        crawl_website_task.delay(pk)
        
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
        drafts = ContentDraft.objects.filter(website_id=pk)
        return Response({
            'published': drafts.filter(status='published').count(),
            'scheduled': drafts.filter(status='scheduled').count(),
            'pending': drafts.filter(status='draft').count(),
            'approved': drafts.filter(status='approved').count(),
            'rejected': drafts.filter(status='rejected').count(),
        })


class WebsitePagesListView(generics.ListAPIView):
    """Returns crawled pages for onboarding preview."""
    serializer_class = ScrapeResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ScrapeResult.objects.filter(website_id=self.kwargs['pk'])