import os
import base64
from PIL import Image

logo_path = r"c:\Users\user\Downloads\Cadence\Cadence\frontend\media\devexhub_logo.png"
if os.path.exists(logo_path):
    with Image.open(logo_path) as img:
        print(f"Dimensions: {img.size}")
    with open(logo_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    print(f"Encoded length: {len(encoded)}")
else:
    print("Logo path does not exist!")
