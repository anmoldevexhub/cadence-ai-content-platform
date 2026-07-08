import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from django.conf import settings
path = os.path.join(settings.BASE_DIR, 'frontend', 'media', 'logos', 'logo_35.png')
print("Exists:", os.path.exists(path))
if os.path.exists(path):
    print("Size:", os.path.getsize(path))
