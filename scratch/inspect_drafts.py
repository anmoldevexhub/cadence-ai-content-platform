import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from content.models import ContentDraft

print("=== CONTENT DRAFTS ===")
for d in ContentDraft.objects.filter(website_id=35):
    print(f"ID: {d.id}, Title: {d.title}, Status: {d.status}")
    print(f"Body: {d.body!r}")
    print(f"Excerpt: {d.excerpt!r}")
    print("-" * 50)
