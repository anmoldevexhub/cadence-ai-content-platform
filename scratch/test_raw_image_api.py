import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cadence_project.settings")
django.setup()

from content.generator import client

try:
    print("Testing client.images.generate with gpt-image-1-mini...")
    response = client.images.generate(
        model="gpt-image-1-mini",
        prompt="A simple blue circle",
        n=1,
        size="1024x1024"
    )
    print("Raw response object:")
    print(response)
    print("Data type:", type(response.data[0]))
    print("URL attribute:", getattr(response.data[0], 'url', 'Not found'))
    print("B64 JSON attribute:", getattr(response.data[0], 'b64_json', 'Not found'))
except Exception as e:
    print("API call failed with exception:")
    print(e)
