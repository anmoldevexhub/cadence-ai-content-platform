import os
import sys
import django
from django.core import serializers

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from django.apps import apps

# Get all models except ContentType and Permission
models_to_dump = []
for model in apps.get_models():
    app_label = model._meta.app_label
    model_name = model._meta.object_name
    if app_label == 'contenttypes' or (app_label == 'auth' and model_name == 'Permission'):
        continue
    models_to_dump.append(model)

# Query all objects from sqlite database
all_objects = []
for model in models_to_dump:
    try:
        queryset = model.objects.using('sqlite').all()
        all_objects.extend(list(queryset))
    except Exception as e:
        print(f"Skipping model {model._meta.label}: {e}")

# Serialize and write to file with UTF-8 encoding
print(f"Serializing {len(all_objects)} objects...")
data = serializers.serialize('json', all_objects, indent=4, use_natural_foreign_keys=True, use_natural_primary_keys=True)

output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sqlite_dump.json')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(data)

print(f"Successfully dumped data to {output_file}")
