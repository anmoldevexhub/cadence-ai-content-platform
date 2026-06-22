import re
import base64
import os

svg_path = r"c:\Users\user\Downloads\Cadence\Cadence\scratch_svgs\test_hybrid_banner.svg"
artifacts_dir = r"C:\Users\user\.gemini\antigravity\brain\05c996e4-020c-4b88-8d54-5f1da297bbff"
output_png = os.path.join(artifacts_dir, "test_hybrid_banner.png")

if not os.path.exists(svg_path):
    print("SVG file not found!")
    exit(1)

with open(svg_path, "r", encoding="utf-8") as f:
    svg_content = f.read()

# Search for the embedded base64 PNG
match = re.search(r'href="data:image/png;base64,([^"]+)"', svg_content)
if not match:
    # Try searching with single quotes
    match = re.search(r"href='data:image/png;base64,([^']+)'", svg_content)

if match:
    b64_data = match.group(1)
    img_data = base64.b64decode(b64_data)
    with open(output_png, "wb") as f:
        f.write(img_data)
    print(f"Successfully extracted PNG to: {output_png}")
else:
    print("Could not find base64-encoded PNG image inside the SVG.")
