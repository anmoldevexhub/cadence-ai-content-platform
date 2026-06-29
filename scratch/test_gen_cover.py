import os
import sys
import django
import logging

# Set up logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

sys.path.append(r"c:\Users\user\Downloads\Cadence\Cadence")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cadence_project.settings")
django.setup()

from content.generator import generate_svg_cover_via_gpt

print("Calling generate_svg_cover_via_gpt...")
try:
    svg_code, png_filename = generate_svg_cover_via_gpt(
        title="Artificial Intelligence vs. Generative AI: Navigating the Complexity",
        category="Technology",
        excerpt="Delve into the practical differences between Artificial Intelligence and Generative AI, and learn how each can be strategically applied to solve unique business challenges."
    )
    print("SUCCESS!")
    print(f"svg_code length: {len(svg_code) if svg_code else 0}")
    print(f"png_filename: {png_filename}")
except Exception as e:
    print("FAILED with exception:")
    import traceback
    traceback.print_exc()
