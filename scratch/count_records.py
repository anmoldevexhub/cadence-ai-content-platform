import os
import sys
import django

# Add workspace directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')

# Initialize Django
django.setup()

from django.apps import apps
from django.db import connections

def count_records(db_alias):
    print(f"\n--- Database: {db_alias} ---")
    for model in apps.get_models():
        model_name = model._meta.object_name
        app_label = model._meta.app_label
        try:
            count = model.objects.using(db_alias).count()
            if count > 0:
                print(f"{app_label}.{model_name}: {count} records")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error counting {app_label}.{model_name}: {e}")

# Check default database (Neon)
count_records('default')

# Check sqlite database by dynamically adding it to connections
from django.conf import settings
import copy

db_config = copy.deepcopy(settings.DATABASES)
db_config['sqlite'] = copy.deepcopy(db_config['default'])
db_config['sqlite']['ENGINE'] = 'django.db.backends.sqlite3'
db_config['sqlite']['NAME'] = os.path.join(settings.BASE_DIR, 'db.sqlite3')
if 'OPTIONS' in db_config['sqlite']:
    # SQLite doesn't support some postgres options, clean them
    db_config['sqlite']['OPTIONS'] = {}

# Override connections
connections.databases.update(db_config)

count_records('sqlite')
