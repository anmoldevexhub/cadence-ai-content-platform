import os
import re
import sys
import django

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from logs.models import ActivityLog
from content.models import ContentDraft

def parse_varint(data, offset):
    val = 0
    for i in range(9):
        if offset + i >= len(data):
            break
        b = data[offset + i]
        val = (val << 7) | (b & 0x7F)
        if not (b & 0x80):
            return val, offset + i + 1
    return val, offset + 9

def get_serial_len(serial_type):
    if serial_type == 0: return 0
    if 1 <= serial_type <= 6:
        return [0, 1, 2, 3, 4, 6, 8][serial_type]
    if serial_type == 7: return 8
    if serial_type == 8: return 0
    if serial_type == 9: return 0
    if serial_type >= 12 and serial_type % 2 == 0:
        return (serial_type - 12) // 2
    if serial_type >= 13 and serial_type % 2 == 1:
        return (serial_type - 13) // 2
    return 0

def recover():
    db_path = 'db.sqlite3'
    if not os.path.exists(db_path):
        print("db.sqlite3 not found!")
        return

    with open(db_path, 'rb') as f:
        data = f.read()

    # Get all blog titles from the activity log containing "for Devexhub" or similar
    logs = ActivityLog.objects.filter(target_description__icontains='Devexhub')
    titles_to_search = []
    for log in logs:
        desc = log.target_description
        # Extract title from desc (e.g. "Title for Devexhub" or "Title @ ...")
        title = desc
        if " for Devexhub" in desc:
            title = desc.split(" for Devexhub")[0]
        elif " @ " in desc:
            title = desc.split(" @ ")[0]
        elif " -> " in desc:
            title = desc.split(" -> ")[0]
        elif " → " in desc:
            title = desc.split(" → ")[0]
        
        # Clean title
        title = title.strip()
        if title and title != "Devexhub" and "Uploaded blog sample" not in title and title not in titles_to_search:
            titles_to_search.append(title)

    # Add other known titles manually
    other_titles = [
        "Agentic AI vs Generative AI: Which AI Model Fits Your Business Goals?",
        "Master Future Search: SEO, AEO & GEO Integration",
        "Avoid Costly AWS Implementation Mistakes: Lessons for Scaling Success",
        "Stop Blaming Marketo. Start Fixing What’s Underneath It.",
        "Stop Blaming Marketo: Uncovering Underlying Issues in Your Marketing Stack",
        "The AWS Implementation Mistakes That Get Expensive at Scale",
        "The Hiring Mistake Every Early-Stage Marketing Team Makes (and the Framework That Fixes It)",
        "Your HubSpot Backend Is Either Powering AI or Poisoning It",
        "Why AI Forecasting in Salesforce Relies More on Data Discipline Than Dashboards",
        "Why AI Forecasting in Salesforce Depends More on Data Discipline Than Dashboards",
        "Future of AI Agents in 2026",
        "SEO vs AEO vs GEO: The 2026 Guide to Winning Search, Answers, and AI",
        "Best Website Design Company in India to Elevate Your Brand Online",
        "Best Website Design Company in India to Grow Your Brand Online",
        "How Goal-Based Agents Help AI Make Better Decisions",
        "How KPI Builder Tools Propel Businesses Towards Faster Growth and Superior Results",
        "How KPI Builder Tools Help Businesses Achieve Faster Growth and Better Results",
        "How AI Transforms Business Operations Daily",
        "How AI Is Changing Everyday Business Operations",
        "Impact of AI in 2026",
        "What is Artificial Intelligence? A Practical Guide"
    ]
    for ot in other_titles:
        if ot not in titles_to_search:
            titles_to_search.append(ot)

    print(f"Searching for {len(titles_to_search)} candidate blog posts...")

    recovered_count = 0
    os.makedirs('recovered_blogs', exist_ok=True)

    for title in titles_to_search:
        title_bytes = title.encode('utf-8')
        # Search for title in database binary
        indices = [m.start() for m in re.finditer(re.escape(title_bytes), data)]
        if not indices:
            continue

        for idx in indices:
            # We found the title value at idx!
            # Let's find the platform value (precedes the title in values)
            # The platforms are: 'blog', 'linkedin', 'instagram', 'youtube'
            platform = None
            plat_start = None
            for p in [b'blog', b'linkedin', b'instagram', b'youtube']:
                p_len = len(p)
                # Check if this platform value immediately precedes the title value
                # (there might be some small padding or rowid/header before,
                # but let's check bytes right before)
                possible_plat = data[idx - p_len : idx]
                if possible_plat == p:
                    platform = p.decode('utf-8')
                    plat_start = idx - p_len
                    break

            if not platform:
                # Let's look slightly further back (e.g. up to 15 bytes)
                for p in [b'blog', b'linkedin', b'instagram', b'youtube']:
                    p_len = len(p)
                    for shift in range(1, 15):
                        possible_plat = data[idx - p_len - shift : idx - shift]
                        if possible_plat == p:
                            platform = p.decode('utf-8')
                            plat_start = idx - p_len - shift
                            break
                    if platform:
                        break

            if not platform:
                continue

            # Let's find the record header. It ends at plat_start.
            # Let's scan backwards from plat_start to find a valid header size
            # that parses to the correct serial types.
            header_found = False
            for hdr_size_guess in range(10, 80):
                hdr_start = plat_start - hdr_size_guess
                if hdr_start < 0:
                    continue
                
                # Check if hdr_start is a valid header start
                # Parse varint for header size
                h_size, next_off = parse_varint(data, hdr_start)
                if h_size == hdr_size_guess:
                    # Let's parse the serial types
                    curr = next_off
                    serial_types = []
                    while curr < plat_start:
                        st, next_curr = parse_varint(data, curr)
                        serial_types.append(st)
                        curr = next_curr
                    
                    # Verify serial types match our schema signature:
                    # st[1] (platform) length must match len(platform)
                    # st[2] (title) length must match len(title)
                    if len(serial_types) >= 4:
                        len_plat = get_serial_len(serial_types[1])
                        len_title = get_serial_len(serial_types[2])
                        if len_plat == len(platform) and len_title == len(title):
                            # SUCCESS! We found the exact record header!
                            header_found = True
                            # Let's extract values using the serial types!
                            val_start = plat_start + len(platform) + len(title)
                            
                            # The body is serial_types[3]
                            body_len = get_serial_len(serial_types[3])
                            body_bytes = data[val_start : val_start + body_len]
                            body = body_bytes.decode('utf-8', errors='replace')
                            
                            # The excerpt is serial_types[4]
                            excerpt_len = get_serial_len(serial_types[4])
                            excerpt_bytes = data[val_start + body_len : val_start + body_len + excerpt_len]
                            excerpt = excerpt_bytes.decode('utf-8', errors='replace')
                            
                            # Write to file
                            filename = f"recovered_blogs/{title.replace(':', '').replace('?', '').replace(' ', '_')[:50]}.md"
                            with open(filename, 'w', encoding='utf-8') as rf:
                                rf.write(f"# {title}\n\n")
                                rf.write(f"**Platform:** {platform.capitalize()}\n")
                                rf.write(f"**Excerpt:** {excerpt}\n\n")
                                rf.write("## Content\n\n")
                                rf.write(body)
                            print(f"Successfully recovered: {title} ({platform}) -> {filename}")
                            recovered_count += 1
                            break
                if header_found:
                    break

    print(f"\nCompleted! Recovered {recovered_count} blogs/posts to recovered_blogs/")

if __name__ == '__main__':
    recover()
