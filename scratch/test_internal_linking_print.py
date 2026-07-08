import os
import django
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from content.models import ContentDraft
from websites.models import ScrapeResult
from django.utils.text import slugify

draft = ContentDraft.objects.get(pk=278)

# Re-run same query logic
targets = []
platform_posts = ContentDraft.objects.filter(
    website=draft.website,
    platform='blog',
    status='published',
    is_deleted=False
).exclude(id=draft.id)

for post in platform_posts:
    title = post.title.strip()
    tags = post.tags if isinstance(post.tags, list) else []
    post_url = f"{draft.website.url.rstrip('/')}/blog/{slugify(title)}"
    targets.append({'title': title, 'tags': tags, 'url': post_url})
    
crawled_posts = ScrapeResult.objects.filter(
    website=draft.website,
    page_type='blog post'
)

for post in crawled_posts:
    title = post.page_title.strip()
    tags = post.categories_tags if isinstance(post.categories_tags, list) else []
    post_url = post.page_url
    if not any(t['url'].rstrip('/') == post_url.rstrip('/') or t['title'].lower() == title.lower() for t in targets):
        targets.append({'title': title, 'tags': tags, 'url': post_url})

print(f"Total targets found: {len(targets)}")
body_text = draft.body.lower()

for target in targets:
    title = target['title']
    tags = target['tags']
    url = target['url']
    
    title_parts = [title] + [t.strip() for t in re.split(r'[:\-]', title) if t.strip() and t.strip() != title]
    keywords = title_parts + [tag for tag in tags if tag and len(tag) >= 3]
    
    print(f"\nTarget: {title} ({url})")
    print(f"Keywords to search: {keywords}")
    
    for kw in keywords:
        pattern = re.compile(rf'\b({re.escape(kw)})\b', re.IGNORECASE)
        match = pattern.search(body_text)
        if match:
            print(f"  -> MATCHED: '{kw}' matched '{match.group(0)}' in body!")
        else:
            print(f"  -> No match for '{kw}'")
