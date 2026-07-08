import re
import os

frontend_dir = r"c:\Users\user\Downloads\Cadence\Cadence\frontend"
css_files = [os.path.join(frontend_dir, f) for f in os.listdir(frontend_dir) if f.endswith(".css")]

for css_file in css_files:
    print("=== File:", os.path.basename(css_file))
    with open(css_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # search for btn-success, data-act, approve, etc.
    for term in ["btn-success", "approve", "data-act"]:
        matches = [line.strip() for line in content.split("\n") if term in line]
        if matches:
            print(f"Term '{term}':")
            for m in matches[:10]:
                print("  ", m)
