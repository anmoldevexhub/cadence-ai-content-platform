from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USERNAME_FIELD = 'email'           # Use email for login
    REQUIRED_FIELDS = ['username']     # username is still required

    email = models.EmailField(unique=True)   # <-- ADD THIS LINE

    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='admin')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='created_users'
    )
    avatar_color = models.CharField(max_length=7, default='#6366f1')
    job_title = models.CharField(max_length=100, default='Content Manager')
    timezone = models.CharField(max_length=100, default='(GMT+05:30) India (Kolkata)')
    bio = models.TextField(blank=True, default='Managing content for specialty brands at Cadence.')
    deleted_at = models.DateTimeField(null=True, blank=True)  # soft-delete / trash
    
    class Meta:
        db_table = 'accounts_user'

    @property
    def initials(self):
        parts = self.get_full_name().split()
        return ''.join(p[0].upper() for p in parts[:2]) if parts else self.username[:2].upper()

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"