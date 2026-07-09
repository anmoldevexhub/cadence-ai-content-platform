from django.db import models
from accounts.models import CustomUser

class LoginLog(models.Model):
    """Every login attempt recorded here."""
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,
                             null=True, related_name='login_logs')
    email = models.EmailField()          # store even if user deleted
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    location_city = models.CharField(max_length=100, blank=True)
    location_country = models.CharField(max_length=100, blank=True)
    success = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        result = "✓" if self.success else "✗"
        return f"{result} {self.email} from {self.ip_address} @ {self.timestamp}"


class ActivityLog(models.Model):
    """All significant actions in the system."""
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('website_add', 'Website Added'),
        ('website_update', 'Website Updated'),
        ('website_delete', 'Website Deleted'),
        ('crawl_start', 'Crawl Started'),
        ('crawl_done', 'Crawl Completed'),
        ('content_idea_submit', 'Content Idea Submitted'),
        ('content_generated', 'Content Generated'),
        ('content_approved', 'Content Approved'),
        ('content_rejected', 'Content Rejected'),
        ('content_regenerated', 'Content Regenerated'),
        ('content_scheduled', 'Content Scheduled'),
        ('content_published', 'Content Published'),
        ('content_update', 'Content Updated'),
        ('user_add', 'User Added'),
        ('user_update', 'User Updated'),
        ('user_delete', 'User Deleted'),
        ('user_signup', 'User Signed Up'),
        ('social_connected', 'Social Account Connected'),
    ]
    
    actor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,
                              null=True, related_name='activity_logs')
    actor_name = models.CharField(max_length=100)       # snapshot in case user deleted
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_description = models.CharField(max_length=300)  # e.g. "Northwind Coffee"
    ip_address = models.GenericIPAddressField(null=True)
    metadata = models.JSONField(default=dict)           # extra context
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.actor_name} → {self.action} → {self.target_description}"