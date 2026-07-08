import os
from PIL import Image

logo_path = r"c:\Users\user\Downloads\Cadence\Cadence\frontend\media\logos\logo_35.png"
print("Exists:", os.path.exists(logo_path))
if os.path.exists(logo_path):
    try:
        im = Image.open(logo_path)
        print("Format:", im.format)
        print("Size:", im.size)
        print("Mode:", im.mode)
        # Check if it has transparency and count colored pixels
        if im.mode == "RGBA":
            extrema = im.getextrema()
            print("Extrema:", extrema)
    except Exception as e:
        print("Error:", e)
