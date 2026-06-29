import os
import sys
import django

sys.path.append(r"c:\Users\user\Downloads\Cadence\Cadence")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cadence_project.settings")
django.setup()

from content.models import ContentIdea, ContentDraft, Website
from content.generator import generate_for_idea

# Get the first website
website = Website.objects.first()
if not website:
    print("No website found!")
    sys.exit(1)

print(f"Using Website: {website.name} ({website.domain})")

# Create a new blog idea
idea = ContentIdea.objects.create(
    website=website,
    platform='blog',
    title="The Future of Autonomous AI Agents in Enterprise Workflows",
    status='pending'
)

print(f"Created ContentIdea ID: {idea.id}")

# Run generation
try:
    print("Running generate_for_idea...")
    draft_id = generate_for_idea(idea.id)
    print(f"Successfully generated Draft ID: {draft_id}")
    
    # Fetch the draft
    draft = ContentDraft.objects.get(id=draft_id)
    print(f"Draft Title: {draft.title}")
    print(f"Draft Cover Image: {draft.cover_image}")
    print(f"Draft Status: {draft.status}")
except Exception as e:
    print("Failed to generate draft:")
    import traceback
    traceback.print_exc()
