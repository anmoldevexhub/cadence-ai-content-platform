import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from content.models import ContentDraft
from websites.models import Website
from content.generator import generate_svg_cover_via_gpt

draft = ContentDraft.objects.get(pk=278)
website = draft.website

print(f"Draft: {draft.title}")
print(f"Website: {website.name}")
print(f"Current Cover Image URL: {draft.cover_image}")

# Run cover image generation
print("Running cover image generation...")
svg, png_filename = generate_svg_cover_via_gpt(
    title=draft.title,
    category=draft.category,
    excerpt=draft.excerpt,
    website=website
)

print("Generated png_filename:", png_filename)
if png_filename:
    cover_image_url = f"/static/media/{png_filename}"
    draft.cover_image = cover_image_url
    draft.save()
    print("New Cover Image URL saved:", draft.cover_image)
