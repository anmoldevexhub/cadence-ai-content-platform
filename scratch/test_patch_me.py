import os, sys, django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from accounts.models import CustomUser
from accounts.serializers import UserSerializer

user = CustomUser.objects.get(username='superadmin')
print(f"Before: first_name={user.first_name!r}, last_name={user.last_name!r}, email={user.email!r}")

# Simulate PATCH data
data = {
    'first_name': 'SuperNew',
    'last_name': 'AdminNew',
    'email': 'superadmin@yopmail.com' # same email
}

serializer = UserSerializer(user, data=data, partial=True)
print("Is valid:", serializer.is_valid())
if not serializer.is_valid():
    print("Errors:", serializer.errors)
else:
    updated_user = serializer.save()
    print(f"After: first_name={updated_user.first_name!r}, last_name={updated_user.last_name!r}, email={updated_user.email!r}")
