import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from content.models import ContentDraft
from content.utils import inject_internal_links
from bs4 import BeautifulSoup

draft = ContentDraft.objects.get(pk=278)

# Temporarily set body with test keywords
test_body = """
<h2>GST Returns Guide</h2>
<p>Filing GST returns is important for compliance. Many businesses need help with their <strong>bookkeeping</strong> and accounting to ensure accuracy. If you are wondering how to manage this, read on.</p>
"""
draft.body = test_body
draft.save()

print("Draft Body set to test body (contains 'bookkeeping').")
print("Running inject_internal_links...")
inject_internal_links(draft)

# Reload and check
draft.refresh_from_db()
print("\nDraft Body after linking:")
print(draft.body)

soup = BeautifulSoup(draft.body, 'html.parser')
links = soup.find_all('a')
print("\nLinks found:")
for link in links:
    print(f"  Href: {link.get('href')}, Text: {link.text}")
