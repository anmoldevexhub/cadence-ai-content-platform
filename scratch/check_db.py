import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from accounts.models import CustomUser
from content.models import BlogPost, Category
from websites.models import Website

print("=== Users ===")
for u in CustomUser.objects.all():
    role = getattr(u, 'role', 'N/A')
    print(f"  {u.id}: {u.username} | {u.email} | role={role}")

print(f"\n=== Websites: {Website.objects.count()} ===")
for w in Website.objects.all()[:5]:
    print(f"  {w.id}: {w.name} | {w.url}")

print(f"\n=== Categories: {Category.objects.count()} ===")
for c in Category.objects.all()[:5]:
    print(f"  {c.id}: {c.name}")

print(f"\n=== Blog Posts: {BlogPost.objects.count()} ===")
for b in BlogPost.objects.all()[:5]:
    print(f"  {b.id}: {b.title[:60]}")
