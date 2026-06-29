import os
import re
import sys
import django
from django.utils import timezone
from datetime import timedelta

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from websites.models import Website, SocialConnection
from content.models import ContentIdea, ContentDraft, ScheduledPost
from logs.models import ActivityLog

User = get_user_model()

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

def restore():
    db_path = 'db.sqlite3'
    if not os.path.exists(db_path):
        print("db.sqlite3 not found!")
        return

    with open(db_path, 'rb') as f:
        data = f.read()

    # Find the owner for the website
    # Try admin@yopmail.com first, then superadmin@yopmail.com, then maya@cadence.io, then devon@cadence.io
    owner = None
    emails_to_try = ['admin@yopmail.com', 'superadmin@yopmail.com', 'maya@cadence.io', 'devon@cadence.io']
    for email in emails_to_try:
        try:
            owner = User.objects.get(email=email)
            print(f"Found owner: {owner.email} (id={owner.id})")
            break
        except User.DoesNotExist:
            continue
            
    if not owner:
        owner = User.objects.first()
        print(f"Fallback to first user as owner: {owner.email if owner else 'None'}")
        
    if not owner:
        print("Error: No users found in database to assign the website to!")
        return

    # 1. Recreate the Devexhub website
    website, created = Website.objects.get_or_create(
        domain="devexhub.in",
        defaults={
            "name": "Devexhub",
            "url": "https://www.devexhub.in",
            "industry": "Technology",
            "tone": "Professional, technical",
            "topics": ["Digital Marketing", "SEO", "Social Media Marketing", "Web Development", "Affiliate Marketing", "Mobile Marketing", "E-commerce Marketing", "Search Engine Optimization"],
            "status": "active",
            "color": "#6366f1",
            "owner": owner,
            "needs_crawl": False,
            "scrape_status": "done",
            "scrape_summary": "### Style Guide for Devexhub.in\n\n#### 1. Writing Tone\n- **Tone**: Conversational yet informative. The content should be professional, technical, and clear.\n\n#### 2. Structure\n- Use subheadings (H2, H3) for readability.\n- Keep paragraphs short and concise."
        }
    )
    if created:
        print(f"Recreated website: {website.name} (id={website.id})")
        # Add social connections
        for platform, handle in [("linkedin", "company/devexhub"), ("youtube", "@devexhub"), ("blog", "devexhub.in/feed")]:
            SocialConnection.objects.get_or_create(
                website=website,
                platform=platform,
                defaults={"make_webhook_url": "https://hook.us1.make.com/demo"}
            )
    else:
        print(f"Website already exists: {website.name} (id={website.id})")

    # Get candidate titles from ActivityLog
    logs = ActivityLog.objects.filter(target_description__icontains='Devexhub')
    titles_to_search = []
    for log in logs:
        desc = log.target_description
        title = desc
        if " for Devexhub" in desc:
            title = desc.split(" for Devexhub")[0]
        elif " @ " in desc:
            title = desc.split(" @ ")[0]
        elif " -> " in desc:
            title = desc.split(" -> ")[0]
        elif " → " in desc:
            title = desc.split(" → ")[0]
        
        title = title.strip()
        if title and title != "Devexhub" and "Uploaded blog sample" not in title and title not in titles_to_search:
            titles_to_search.append(title)

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

    print(f"Restoring drafts for {len(titles_to_search)} candidate titles...")

    restored_count = 0
    for title in titles_to_search:
        title_bytes = title.encode('utf-8')
        indices = [m.start() for m in re.finditer(re.escape(title_bytes), data)]
        if not indices:
            continue

        for idx in indices:
            # Locate platform
            platform = None
            plat_start = None
            for p in [b'blog', b'linkedin', b'instagram', b'youtube']:
                p_len = len(p)
                possible_plat = data[idx - p_len : idx]
                if possible_plat == p:
                    platform = p.decode('utf-8')
                    plat_start = idx - p_len
                    break

            if not platform:
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

            # Parse record header
            header_found = False
            for hdr_size_guess in range(10, 80):
                hdr_start = plat_start - hdr_size_guess
                if hdr_start < 0:
                    continue
                
                h_size, next_off = parse_varint(data, hdr_start)
                if h_size == hdr_size_guess:
                    curr = next_off
                    serial_types = []
                    while curr < plat_start:
                        st, next_curr = parse_varint(data, curr)
                        serial_types.append(st)
                        curr = next_curr
                    
                    if len(serial_types) >= 9:
                        len_plat = get_serial_len(serial_types[1])
                        len_title = get_serial_len(serial_types[2])
                        if len_plat == len(platform) and len_title == len(title):
                            header_found = True
                            
                            val_start = plat_start + len(platform) + len(title)
                            
                            # Extract fields
                            body_len = get_serial_len(serial_types[3])
                            body = data[val_start : val_start + body_len].decode('utf-8', errors='replace')
                            
                            excerpt_len = get_serial_len(serial_types[4])
                            excerpt = data[val_start + body_len : val_start + body_len + excerpt_len].decode('utf-8', errors='replace')
                            
                            # Column 8 is status
                            # Cumulative offset of fields before status:
                            # platform (1), title (2), body (3), excerpt (4), meta_description (5), tags (6), word_count (7)
                            meta_desc_len = get_serial_len(serial_types[5])
                            tags_len = get_serial_len(serial_types[6])
                            word_count_len = get_serial_len(serial_types[7])
                            
                            status_offset = val_start + body_len + excerpt_len + meta_desc_len + tags_len + word_count_len
                            status_len = get_serial_len(serial_types[8])
                            status = data[status_offset : status_offset + status_len].decode('utf-8', errors='replace')
                            
                            # Sanitize status values
                            if status not in ['draft', 'approved', 'rejected', 'scheduled', 'published']:
                                status = 'draft'

                            # 2. Recreate ContentIdea
                            idea, idea_created = ContentIdea.objects.get_or_create(
                                website=website,
                                title=title,
                                platform=platform,
                                defaults={
                                    "submitted_by": owner,
                                    "status": "done"
                                }
                            )

                            # 3. Recreate ContentDraft
                            draft, draft_created = ContentDraft.objects.get_or_create(
                                idea=idea,
                                website=website,
                                platform=platform,
                                title=title,
                                defaults={
                                    "body": body,
                                    "excerpt": excerpt,
                                    "status": status,
                                }
                            )
                            
                            if draft_created:
                                print(f"  Restored draft: '{title[:50]}' as [{status}]")
                                restored_count += 1
                                
                                # 4. If scheduled or published, create ScheduledPost
                                if status in ['scheduled', 'published']:
                                    scheduled_date = timezone.now() + (timedelta(days=1) if status == 'scheduled' else timedelta(days=-1))
                                    ScheduledPost.objects.get_or_create(
                                        draft=draft,
                                        defaults={
                                            "scheduled_for": scheduled_date,
                                            "is_published": (status == 'published'),
                                            "published_at": scheduled_date if status == 'published' else None
                                        }
                                    )
                            break
                if header_found:
                    break

    print(f"\nCompleted! Re-imported {restored_count} drafts/posts into the live database under 'Devexhub'.")

if __name__ == '__main__':
    restore()
