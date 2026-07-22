from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
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


def send_invite_email(invited_user, invited_by, password, request=None):
    """Send a welcome/invite email to a newly created admin."""
    try:
        # Build the absolute login URL
        if request:
            login_url = request.build_absolute_uri('/static/login.html')
        else:
            login_url = 'http://127.0.0.1:8006/static/login.html'

        full_name = invited_user.get_full_name() or invited_user.username
        inviter_name = invited_by.get_full_name() or invited_by.username
        role_display = 'Super Admin' if invited_user.role == 'super_admin' else 'Admin'

        subject = f"You've been invited to Candence as {role_display}"

        text_body = f"""Hi {full_name},

{inviter_name} has added you to Candence as {role_display}.

Your login details:
  Email:    {invited_user.email}
  Password: {password}

Sign in here: {login_url}

Please change your password after logging in.

The Candence Team"""

        html_body = f"""
<div style="font-family:Inter,sans-serif;max-width:520px;margin:0 auto;padding:32px 24px;background:#f8fafc">
  <div style="background:#fff;border-radius:16px;padding:40px;box-shadow:0 1px 3px rgba(0,0,0,.08)">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:32px">
      <div style="width:36px;height:36px;background:#6366f1;border-radius:10px;display:flex;align-items:center;justify-content:center">
        <span style="color:#fff;font-size:18px;font-weight:700">&#9835;</span>
      </div>
      <span style="font-size:20px;font-weight:700;color:#1e293b">Candence</span>
    </div>
    <h1 style="font-size:22px;font-weight:700;color:#1e293b;margin:0 0 8px">You're invited! &#127881;</h1>
    <p style="color:#64748b;margin:0 0 28px;line-height:1.6">
      <strong>{inviter_name}</strong> has added you to <strong>Candence</strong> as <strong>{role_display}</strong>.
    </p>
    <div style="background:#f1f5f9;border-radius:10px;padding:20px;margin-bottom:28px">
      <p style="margin:0 0 10px;font-size:13px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:.5px">Your login details</p>
      <p style="margin:0 0 6px;color:#1e293b"><strong>Email:</strong> {invited_user.email}</p>
      <p style="margin:0;color:#1e293b"><strong>Temporary password:</strong> <code style="background:#e2e8f0;padding:2px 6px;border-radius:4px">{password}</code></p>
    </div>
    <a href="{login_url}" style="display:inline-block;background:#6366f1;color:#fff;text-decoration:none;padding:12px 28px;border-radius:10px;font-weight:600;font-size:15px">Sign in to Candence</a>
    <p style="margin:24px 0 0;font-size:12px;color:#94a3b8">Please change your password after your first login.</p>
  </div>
</div>"""

        send_mail(
            subject=subject,
            message=text_body,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invited_user.email],
            html_message=html_body,
            fail_silently=True,
        )
    except Exception as e:
        # Non-critical — log but don't break the API response
        import logging
        logging.getLogger(__name__).warning(f'Failed to send invite email: {e}')


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
            actor=user, actor_name=user.get_full_name() or user.username,
            action='login', target_description='',
            ip_address=ip
        )
        
        # Explicitly stamp last_login so the admin table shows current time
        from django.utils import timezone as tz
        user.last_login = tz.now()
        user.save(update_fields=['last_login'])
        
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
            actor=request.user, actor_name=request.user.get_full_name() or request.user.username,
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
    queryset = CustomUser.objects.filter(deleted_at__isnull=True).order_by('-date_joined')
    
    def get_serializer_class(self):
        return UserCreateSerializer if self.request.method == 'POST' else UserSerializer

    def perform_create(self, serializer):
        ip, _ = get_client_ip(self.request)
        # Generate a random secure password for the invite
        import secrets
        raw_password = secrets.token_urlsafe(12)
        # Override the password in serializer with the generated password
        serializer.validated_data['password'] = raw_password
        user = serializer.save(created_by=self.request.user)
        ActivityLog.objects.create(
            actor=self.request.user, actor_name=self.request.user.get_full_name() or self.request.user.username,
            action='user_add', target_description=user.get_full_name() or user.username,
            ip_address=ip
        )
        # Send invite email (non-blocking, fail_silently=True)
        send_invite_email(
            invited_user=user,
            invited_by=self.request.user,
            password=raw_password,
            request=self.request,
        )


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Super Admin: view/update/delete a user."""
    permission_classes = [IsSuperAdmin]
    queryset = CustomUser.objects.filter(deleted_at__isnull=True)
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
        
        # Check if password is in request data to manually update it
        password = self.request.data.get('password')
        if password:
            user.set_password(password)
            user.save()
            
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
                actor_name=self.request.user.get_full_name() or self.request.user.username,
                action='user_update',
                target_description=user.get_full_name() or user.username,
                ip_address=ip,
                metadata={'changes': changes}
            )

    def perform_destroy(self, instance):
        ip, _ = get_client_ip(self.request)
        ActivityLog.objects.create(
            actor=self.request.user, actor_name=self.request.user.get_full_name() or self.request.user.username,
            action='user_delete', target_description=instance.get_full_name() or instance.username,
            ip_address=ip
        )
        # Soft‑delete: mark as trashed instead of hard delete
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save()



class TrashUserListView(generics.ListAPIView):
    """Super Admin: list all soft‑deleted users (trash)."""
    permission_classes = [IsSuperAdmin]
    queryset = CustomUser.objects.filter(deleted_at__isnull=False).order_by('-deleted_at')
    serializer_class = UserSerializer

class UserRestoreView(APIView):
    """Super Admin: restore a trashed user (undo soft‑delete)."""
    permission_classes = [IsSuperAdmin]
    def post(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk, deleted_at__isnull=False)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found or not in trash.'}, status=404)
        user.deleted_at = None
        user.save()
        ActivityLog.objects.create(
            actor=request.user,
            actor_name=request.user.get_full_name() or request.user.username,
            action='user_restore',
            target_description=user.get_full_name() or user.username,
            ip_address=get_client_ip(request)[0]
        )
        return Response({'detail': 'User restored.'})

class UserPurgeView(APIView):
    """Super Admin: permanently delete a trashed user from the database."""
    permission_classes = [IsSuperAdmin]
    def delete(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk, deleted_at__isnull=False)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found or not in trash.'}, status=404)
        ActivityLog.objects.create(
            actor=request.user,
            actor_name=request.user.get_full_name() or request.user.username,
            action='user_purge',
            target_description=user.get_full_name() or user.username,
            ip_address=get_client_ip(request)[0]
        )
        user.delete()
        return Response({'detail': 'User permanently removed.'})

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
                actor_name=user.get_full_name() or user.username,
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


@method_decorator(csrf_exempt, name='dispatch')
class PasswordResetRequestView(APIView):
    """Send a password reset email with a token link."""
    permission_classes = [AllowAny]

    def post(self, request):
        import secrets
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({'detail': 'Email is required.'}, status=400)

        # Always return success to avoid email enumeration
        try:
            user = CustomUser.objects.get(email__iexact=email, deleted_at__isnull=True)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'If this email exists, a reset link has been sent.'})

        # Generate a secure token and store it with expiry
        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_token_expires = timezone.now() + timezone.timedelta(minutes=30)
        user.save(update_fields=['password_reset_token', 'password_reset_token_expires'])

        # Build the reset URL
        if request:
            reset_url = request.build_absolute_uri(f'/static/reset-password.html?token={token}')
        else:
            reset_url = f'http://127.0.0.1:8006/static/reset-password.html?token={token}'

        full_name = user.get_full_name() or user.username

        subject = "Reset your Candence password"
        text_body = f"""Hi {full_name},

We received a request to reset your Candence password.

Click the link below to set a new password (expires in 30 minutes):
{reset_url}

If you didn't request this, you can safely ignore this email.

The Candence Team"""

        html_body = f"""
<div style="font-family:Inter,sans-serif;max-width:520px;margin:0 auto;padding:32px 24px;background:#f8fafc">
  <div style="background:#fff;border-radius:16px;padding:40px;box-shadow:0 1px 3px rgba(0,0,0,.08)">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:32px">
      <div style="width:36px;height:36px;background:#095075;border-radius:10px;display:flex;align-items:center;justify-content:center">
        <span style="color:#fff;font-size:18px;font-weight:700">&#9835;</span>
      </div>
      <span style="font-size:20px;font-weight:700;color:#1e293b">Candence</span>
    </div>
    <h1 style="font-size:22px;font-weight:700;color:#1e293b;margin:0 0 8px">Reset your password 🔐</h1>
    <p style="color:#64748b;margin:0 0 28px;line-height:1.6">
      Hi <strong>{full_name}</strong>, we received a request to reset your password.
      Click the button below — the link expires in <strong>30 minutes</strong>.
    </p>
    <a href="{reset_url}" style="display:inline-block;background:#095075;color:#fff;text-decoration:none;padding:12px 28px;border-radius:10px;font-weight:600;font-size:15px">Reset Password</a>
    <p style="margin:24px 0 0;font-size:12px;color:#94a3b8">If you didn't request a password reset, you can safely ignore this email.</p>
  </div>
</div>"""

        try:
            send_mail(
                subject=subject,
                message=text_body,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_body,
                fail_silently=False,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'Failed to send password reset email: {e}')
            return Response({'detail': 'Failed to send email. Please try again later.'}, status=500)

        return Response({'detail': 'If this email exists, a reset link has been sent.'})


@method_decorator(csrf_exempt, name='dispatch')
class PasswordResetConfirmView(APIView):
    """Validate the reset token and set the new password."""
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token', '').strip()
        new_password = request.data.get('password', '').strip()

        if not token or not new_password:
            return Response({'detail': 'Token and new password are required.'}, status=400)

        if len(new_password) < 8:
            return Response({'detail': 'Password must be at least 8 characters.'}, status=400)

        try:
            user = CustomUser.objects.get(
                password_reset_token=token,
                deleted_at__isnull=True
            )
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Invalid or expired reset link.'}, status=400)

        # Check token expiry
        if user.password_reset_token_expires and timezone.now() > user.password_reset_token_expires:
            return Response({'detail': 'Reset link has expired. Please request a new one.'}, status=400)

        # Set new password and clear the token
        user.set_password(new_password)
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.save(update_fields=['password', 'password_reset_token', 'password_reset_token_expires'])

        return Response({'detail': 'Password reset successfully. You can now log in.'})