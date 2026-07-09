import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

print("Neon Users:")
for u in User.objects.using('default').all():
    print(f"ID: {u.id}, Email: {u.email}, Username: {u.username}")

# Configure SQLite connection
from django.conf import settings
from django.db import connections
import copy

db_config = copy.deepcopy(settings.DATABASES)
db_config['sqlite'] = copy.deepcopy(db_config['default'])
db_config['sqlite']['ENGINE'] = 'django.db.backends.sqlite3'
db_config['sqlite']['NAME'] = os.path.join(settings.BASE_DIR, 'db.sqlite3')
if 'OPTIONS' in db_config['sqlite']:
    db_config['sqlite']['OPTIONS'] = {}

connections.databases.update(db_config)

print("\nSQLite Users:")
for u in User.objects.using('sqlite').all():
    print(f"ID: {u.id}, Email: {u.email}, Username: {u.username}")
