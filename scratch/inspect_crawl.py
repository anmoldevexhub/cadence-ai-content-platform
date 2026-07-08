import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from websites.models import Website, ScrapeResult

print("=== WEBSITES ===")
for w in Website.objects.all():
    print(f"ID: {w.id}, Name: {w.name}, Domain: {w.domain}, URL: {w.url}, Logo URL: {w.logo_url}")
    print(f"Scrape Status: {w.scrape_status}, Need Crawl: {w.needs_crawl}")
    print(f"Scrape Summary (first 200 chars): {w.scrape_summary[:200]}")
    print(f"Style Guide: {w.style_guide}")
    print("-" * 40)

print("=== SCRAPED PAGES ===")
for r in ScrapeResult.objects.all():
    if "techvigya" in r.page_url:
        print(f"Web ID: {r.website.id}, URL: {r.page_url}, Title: {r.page_title}, Type: {r.page_type}")
        print(f"Heading Structure: {r.heading_structure}")
        print(f"Raw Text (first 200 chars): {r.raw_text[:200]!r}")
        print(f"Main Content (first 200 chars): {r.main_content[:200]!r}")
        print("=" * 40)
