import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from accounts.models import CustomUser
from content.models import ContentDraft, ContentIdea
from websites.models import Website

print("=== Users ===")
for u in CustomUser.objects.all():
    role = getattr(u, 'role', 'N/A')
    print(f"  {u.id}: {u.username} | {u.email} | role={role}")

print(f"\n=== Websites: {Website.objects.count()} ===")
for w in Website.objects.all()[:5]:
    print(f"  {w.id}: {w.name} | {w.url}")

print(f"\n=== Content Ideas: {ContentIdea.objects.count()} ===")
for ci in ContentIdea.objects.all()[:5]:
    print(f"  {ci.id}: {ci.title} | {ci.platform}")

print(f"\n=== Content Drafts: {ContentDraft.objects.count()} ===")
for d in ContentDraft.objects.all()[:5]:
    print(f"  {d.id}: {d.title[:60]}")

