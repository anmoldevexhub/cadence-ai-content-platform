import os, sys, django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from accounts.models import CustomUser

print("Resetting passwords...")
for u in CustomUser.objects.all():
    u.set_password("demo1234")
    u.save()
    print(f"Password reset for {u.username} ({u.email})")
