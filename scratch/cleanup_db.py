import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from websites.models import Website
from logs.models import ActivityLog, LoginLog

User = get_user_model()

print("Starting database cleanup...")

# 1. Delete all websites (this cascades to ScrapeResult, SampleContent, ScheduledPost, ContentDraft, ContentIdea, SocialConnection)
websites_count = Website.objects.count()
print(f"Deleting {websites_count} websites...")
Website.objects.all().delete()

# 2. Delete all users except superadmin
users_to_delete = User.objects.exclude(username='superadmin')
users_count = users_to_delete.count()
print(f"Deleting {users_count} dummy users...")
users_to_delete.delete()

# 3. Clean up all logs
print("Clearing activity and login logs...")
ActivityLog.objects.all().delete()
LoginLog.objects.all().delete()

print("Database cleanup completed successfully! Remaining users:")
for u in User.objects.all():
    print(f"- {u.username} ({u.email}) [role={u.role}]")
