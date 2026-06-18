from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from ipware import get_client_ip # type: ignore
import user_agents
import requests

from .models import CustomUser
from .serializers import (UserSerializer, UserCreateSerializer,
                          LoginSerializer, ChangePasswordSerializer)
from .permissions import IsSuperAdmin, IsAdminOrSuperAdmin
from logs.models import LoginLog, ActivityLog


def get_location(ip):
    """Free IP geolocation via ip-api.com (no API key needed, 45 req/min)."""
    try:
        r = requests.get(f'http://ip-api.com/json/{ip}?fields=city,country', timeout=3)
        data = r.json()
        return data.get('city', ''), data.get('country', '')
    except Exception:
        return '', ''


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(request, username=email, password=password)
        
        ip, _ = get_client_ip(request)
        ua_string = request.META.get('HTTP_USER_AGENT', '')
        city, country = get_location(ip) if ip else ('', '')
        
        if user is None or not user.is_active:
            LoginLog.objects.create(
                user=None, email=email, ip_address=ip,
                user_agent=ua_string, location_city=city,
                location_country=country, success=False
            )
            return Response({'detail': 'Invalid credentials.'}, status=401)
        
        # Successful login
        LoginLog.objects.create(
            user=user, email=email, ip_address=ip,
            user_agent=ua_string, location_city=city,
            location_country=country, success=True
        )
        ActivityLog.objects.create(
            actor=user, actor_name=user.get_full_name(),
            action='login', target_description='',
            ip_address=ip
        )
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ip, _ = get_client_ip(request)
        ActivityLog.objects.create(
            actor=request.user, actor_name=request.user.get_full_name(),
            action='logout', target_description='',
            ip_address=ip
        )
        # Blacklist the refresh token
        try:
            token = RefreshToken(request.data.get('refresh'))
            token.blacklist()
        except Exception:
            pass
        return Response({'detail': 'Logged out.'})


class UserListCreateView(generics.ListCreateAPIView):
    """Super Admin: list all users / create new admin."""
    permission_classes = [IsSuperAdmin]
    queryset = CustomUser.objects.all().order_by('-date_joined')
    
    def get_serializer_class(self):
        return UserCreateSerializer if self.request.method == 'POST' else UserSerializer

    def perform_create(self, serializer):
        ip, _ = get_client_ip(self.request)
        user = serializer.save(created_by=self.request.user)
        ActivityLog.objects.create(
            actor=self.request.user, actor_name=self.request.user.get_full_name(),
            action='user_add', target_description=user.get_full_name(),
            ip_address=ip
        )


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Super Admin: view/update/delete a user."""
    permission_classes = [IsSuperAdmin]
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def perform_update(self, serializer):
        instance = self.get_object()
        old_data = {
            'email': instance.email,
            'role': instance.role,
            'is_active': instance.is_active,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
        }
        user = serializer.save()
        new_data = {
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'first_name': user.first_name,
            'last_name': user.last_name,
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
                action='user_update',
                target_description=user.get_full_name(),
                ip_address=ip,
                metadata={'changes': changes}
            )

    def perform_destroy(self, instance):
        ip, _ = get_client_ip(self.request)
        ActivityLog.objects.create(
            actor=self.request.user, actor_name=self.request.user.get_full_name(),
            action='user_delete', target_description=instance.get_full_name(),
            ip_address=ip
        )
        instance.delete()


class MeView(APIView):
    """Returns logged-in user's profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        instance = request.user
        old_data = {
            'email': instance.email,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'avatar_color': instance.avatar_color,
        }
        serializer = UserSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        new_data = {
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar_color': user.avatar_color,
        }
        ip, _ = get_client_ip(request)
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
                actor=user,
                actor_name=user.get_full_name(),
                action='user_update',
                target_description=f"Self Profile ({user.username})",
                ip_address=ip,
                metadata={'changes': changes}
            )
        return Response(serializer.data)


class RegisterView(generics.CreateAPIView):
    """Allows public user registration."""
    permission_classes = [AllowAny]
    serializer_class = UserCreateSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        ip, _ = get_client_ip(self.request)
        # We don't have a request.user since the user is not logged in yet.
        # We can create ActivityLog with actor=user.
        ActivityLog.objects.create(
            actor=user, actor_name=user.get_full_name() or user.username,
            action='user_signup', target_description=user.get_full_name() or user.username,
            ip_address=ip
        )