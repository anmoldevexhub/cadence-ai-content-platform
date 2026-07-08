import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from websites.models import Website

# Find websites using the old default color
old_color = '#6366f1'
new_color = '#095075'

query = Website.objects.filter(color__iexact=old_color)
print(f"Found {query.count()} websites using color {old_color}")

updated_count = 0
for site in query:
    print(f"Updating website: {site.name} (ID: {site.id})")
    site.color = new_color
    site.save()
    updated_count += 1

print(f"Successfully updated {updated_count} websites to color {new_color}")
