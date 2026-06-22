import os, sys, django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from accounts.models import CustomUser

print("=== Users in DB ===")
for u in CustomUser.objects.all():
    print(f"ID: {u.id}")
    print(f"  Username: {u.username}")
    print(f"  Email: {u.email}")
    print(f"  First Name: {u.first_name!r}")
    print(f"  Last Name: {u.last_name!r}")
    print(f"  Role: {u.role}")
    print("-" * 30)
