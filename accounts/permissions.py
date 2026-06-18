from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                request.user.role == 'super_admin')

class IsAdminOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                request.user.role in ['admin', 'super_admin'])