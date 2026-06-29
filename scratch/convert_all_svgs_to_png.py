import os
import sys
import re
import base64
import django

sys.path.append(r"c:\Users\user\Downloads\Cadence\Cadence")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cadence_project.settings")
django.setup()

from django.conf import settings
from content.models import ContentDraft

# Regex to match base64 image in SVG
b64_pattern = re.compile(r'href="data:image/png;base64,([^"]+)"')

print("Starting SVG to PNG conversion for existing drafts...")

drafts_with_svg = ContentDraft.objects.filter(cover_image__endswith='.svg')
print(f"Found {drafts_with_svg.count()} drafts referencing SVG cover images.")

converted_count = 0
skipped_count = 0

for draft in drafts_with_svg:
    cover_image_path = draft.cover_image
    # Get relative path from /static/media/
    rel_path = cover_image_path.replace('/static/media/', '').replace('/static/', '')
    svg_filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', os.path.basename(rel_path))
    
    if not os.path.exists(svg_filepath):
        # Try just 'frontend/static/media' or similar if path differs
        svg_filepath = os.path.join(settings.BASE_DIR, 'frontend', rel_path)
        
    if not os.path.exists(svg_filepath):
        print(f"[-] SVG file does not exist: {cover_image_path} (resolved to {svg_filepath}). Skipping.")
        skipped_count += 1
        continue
        
    try:
        with open(svg_filepath, 'r', encoding='utf-8', errors='ignore') as f:
            svg_content = f.read()
            
        match = b64_pattern.search(svg_content)
        if match:
            b64_data = match.group(1)
            png_bytes = base64.b64decode(b64_data)
            
            # Construct new PNG filename
            base_name = os.path.splitext(os.path.basename(svg_filepath))[0]
            png_filename = f"{base_name}.png"
            png_filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', png_filename)
            
            with open(png_filepath, 'wb') as png_f:
                png_f.write(png_bytes)
                
            # Update database
            new_cover_url = f"/static/media/{png_filename}"
            draft.cover_image = new_cover_url
            draft.save(update_fields=['cover_image'])
            
            print(f"[+] Converted Draft ID {draft.id}: {cover_image_path} -> {new_cover_url}")
            converted_count += 1
        else:
            # It might be a fallback SVG (without embedded PNG)
            print(f"[*] Draft ID {draft.id}: SVG does not contain embedded PNG base64 data. Skipping conversion, but record remains.")
            skipped_count += 1
    except Exception as e:
        print(f"[!] Error processing Draft ID {draft.id}: {e}")
        skipped_count += 1

print(f"\nConversion complete! Converted: {converted_count}, Skipped/Raw: {skipped_count}")
