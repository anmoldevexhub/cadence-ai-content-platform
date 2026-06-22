import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cadence_project.settings")
django.setup()

from content.generator import generate_svg_cover_via_gpt

print("Starting PHP Web Development banner generation test...")
svg = generate_svg_cover_via_gpt(
    title="A Deep Dive into Modern PHP 8.3 Features",
    category="Web Development",
    excerpt="Discover read-only classes, intersection types, custom attributes, and performance improvements in PHP 8.3.",
    website=None
)

print(f"Generated SVG length: {len(svg)}")
output_path = r"c:\Users\user\Downloads\Cadence\Cadence\scratch_svgs\test_hybrid_banner.svg"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(svg)

print(f"Saved test output to: {output_path}")
