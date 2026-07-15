import os
import django
import sys

# Add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from content.views import RegenerateDraftView
from accounts.models import CustomUser
from content.models import ContentDraft

# Verify draft 504 exists
draft_id = 504
if not ContentDraft.objects.filter(pk=draft_id).exists():
    # If 504 doesn't exist, pick the latest draft
    latest_draft = ContentDraft.objects.order_by('-id').first()
    if latest_draft:
        draft_id = latest_draft.id
    else:
        print("No draft found in DB to test with")
        sys.exit(1)

print(f"Testing with draft ID: {draft_id}")

factory = APIRequestFactory()
# Request regeneration of type 'content'
request = factory.post(f'/api/content/drafts/{draft_id}/regenerate/', {'type': 'content'}, format='json')

# Authenticate as superadmin or admin
user = CustomUser.objects.filter(role='super').first() or CustomUser.objects.filter(role='admin').first() or CustomUser.objects.first()
if not user:
    print("No user found in DB")
    sys.exit(1)

force_authenticate(request, user=user)
print(f"Testing with user: {user.email} (Role: {user.role})")

view = RegenerateDraftView.as_view()
try:
    response = view(request, pk=draft_id)
    print("Response status code:", response.status_code)
    if hasattr(response, 'data'):
        print("Response data:", response.data)
    else:
        print("Response content:", response.content)
except Exception as e:
    import traceback
    traceback.print_exc()
