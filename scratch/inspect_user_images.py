import os
from PIL import Image

artifacts_dir = r"C:\Users\user\.gemini\antigravity\brain\05c996e4-020c-4b88-8d54-5f1da297bbff"
img1_path = os.path.join(artifacts_dir, "media__1781848761677.png")
img2_path = os.path.join(artifacts_dir, "media__1781848829033.png")

for path, name in [(img1_path, "Pic 1 (media__1781848761677.png)"), (img2_path, "Pic 2 (media__1781848829033.png)")]:
    if os.path.exists(path):
        with Image.open(path) as img:
            print(f"{name}: size={img.size}, format={img.format}, mode={img.mode}")
    else:
        print(f"{name} not found at {path}")
