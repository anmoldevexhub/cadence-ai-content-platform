from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import LoginLog, ActivityLog
from .serializers import LoginLogSerializer, ActivityLogSerializer
from accounts.permissions import IsSuperAdmin, IsAdminOrSuperAdmin


class LoginLogListView(generics.ListAPIView):
    """Super Admin only: see all login attempts."""
    serializer_class = LoginLogSerializer
    permission_classes = [IsSuperAdmin]
    queryset = LoginLog.objects.all()[:200]


class ActivityLogListView(generics.ListAPIView):
    """All admins can see activity; super admin sees all."""
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = ActivityLog.objects.all()
        if user.role != 'super_admin':
            qs = qs.filter(actor=user)
        return qs[:200]


class DashboardAnalyticsView(APIView):
    """Returns summary stats for the dashboard cards."""
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        from content.models import ContentDraft
        from websites.models import Website
        
        user = request.user
        
        if user.role == 'super_admin':
            websites_qs = Website.objects.all()
            drafts_qs = ContentDraft.objects.all()
        else:
            websites_qs = Website.objects.filter(owner=user)
            drafts_qs = ContentDraft.objects.filter(website__owner=user)
        
        recent_activity = ActivityLog.objects.all()[:10] if user.role == 'super_admin' \
            else ActivityLog.objects.filter(actor=user)[:10]
        
        return Response({
            'total_websites': websites_qs.count(),
            'total_drafts': drafts_qs.count(),
            'pending_approval': drafts_qs.filter(status='draft').count(),
            'scheduled': drafts_qs.filter(status='scheduled').count(),
            'published': drafts_qs.filter(status='published').count(),
            'activity': ActivityLogSerializer(recent_activity, many=True).data,
        })