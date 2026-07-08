import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from content.models import ContentDraft, ScheduledPost
from django.utils import timezone

print("Current local/UTC time:", timezone.now())

# Find all published posts
published_drafts = ContentDraft.objects.filter(status='published')
print(f"\nTotal Published Drafts: {published_drafts.count()}")

# Find all scheduled posts
scheduled_posts = ScheduledPost.objects.all()
print(f"\nTotal ScheduledPost records in DB: {scheduled_posts.count()}")

print("\nDetail of ScheduledPost records:")
for sp in scheduled_posts:
    print(f"ID: {sp.id} | Draft Title: '{sp.draft.title}' | Status: {sp.draft.status} | Scheduled For: {sp.scheduled_for} | Is Published: {sp.is_published} | Published At: {sp.published_at}")
