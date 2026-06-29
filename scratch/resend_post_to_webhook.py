import os
import sys
import django

sys.path.append(r"c:\Users\user\Downloads\Cadence\Cadence")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cadence_project.settings")
django.setup()

from content.models import ScheduledPost
from content.publisher import send_to_make

try:
    sp = ScheduledPost.objects.get(draft_id=257)
    print(f"Found ScheduledPost ID: {sp.id} for Draft ID: 257")
    print(f"Title: {sp.draft.title}")
    print(f"Cover Image: {sp.draft.cover_image}")
    
    print("Re-sending to Make.com webhook...")
    res = send_to_make(sp)
    print("SUCCESS!")
    print(f"Response: {res}")
except Exception as e:
    print("Failed to re-send to webhook:")
    import traceback
    traceback.print_exc()
