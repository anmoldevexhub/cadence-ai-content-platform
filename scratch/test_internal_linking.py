import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from content.models import ContentDraft
from content.utils import inject_internal_links

draft = ContentDraft.objects.get(pk=278)
print("Draft Title:", draft.title)
print("Draft Body before linking (contains <a> tags?):", "<a>" in draft.body)

# Run internal links injector
print("Running inject_internal_links...")
inject_internal_links(draft)

# Reload from database
draft.refresh_from_db()
print("Draft Body after linking (contains <a> tags?):", "<a>" in draft.body or "<a href" in draft.body)

# Print all anchor tags found in the body
from bs4 import BeautifulSoup
soup = BeautifulSoup(draft.body, 'html.parser')
links = soup.find_all('a')
print("Links found in body:")
for link in links:
    print(f"  Href: {link.get('href')}, Text: {link.text}")
