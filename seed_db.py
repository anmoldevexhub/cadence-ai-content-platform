import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from websites.models import Website, SocialConnection
from content.models import ContentIdea, ContentDraft, ScheduledPost
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def seed():
    print("Clearing database...")
    ScheduledPost.objects.all().delete()
    ContentDraft.objects.all().delete()
    ContentIdea.objects.all().delete()
    SocialConnection.objects.all().delete()
    Website.objects.all().delete()
    User.objects.all().delete()

    print("Creating users...")
    users_data = [
        {"email": "devon@cadence.io", "username": "devon", "first_name": "Devon", "last_name": "Park", "role": "super_admin", "avatar_color": "#9333ea", "is_superuser": True, "is_staff": True},
        {"email": "maya@cadence.io", "username": "maya", "first_name": "Maya", "last_name": "Chen", "role": "admin", "avatar_color": "#6366f1"},
        {"email": "aisha@cadence.io", "username": "aisha", "first_name": "Aisha", "last_name": "Bello", "role": "admin", "avatar_color": "#0ea5e9"},
        {"email": "marcus@cadence.io", "username": "marcus", "first_name": "Marcus", "last_name": "Lee", "role": "admin", "avatar_color": "#16a34a"},
    ]
    
    users = {}
    for ud in users_data:
        is_super = ud.pop("is_superuser", False)
        is_staff = ud.pop("is_staff", False)
        u = User.objects.create_user(
            email=ud["email"],
            username=ud["username"],
            first_name=ud["first_name"],
            last_name=ud["last_name"],
            role=ud["role"],
            avatar_color=ud["avatar_color"],
            is_active=True
        )
        u.set_password("demo1234")
        if is_super:
            u.is_superuser = True
            u.is_staff = True
        u.save()
        users[ud["username"]] = u
    
    print("Creating websites...")
    websites_data = [
        {
            "id_str": "northwind",
            "name": "Northwind Coffee",
            "domain": "northwindcoffee.com",
            "url": "https://northwindcoffee.com",
            "industry": "Food & Beverage",
            "tone": "Warm, artisanal",
            "topics": ["Specialty coffee", "Brewing guides", "Sustainability"],
            "status": "active",
            "color": "#b45309",
            "owner": users["maya"]
        },
        {
            "id_str": "lumen",
            "name": "Lumen Fitness",
            "domain": "lumenfit.app",
            "url": "https://lumenfit.app",
            "industry": "Health & Fitness",
            "tone": "Energetic, motivating",
            "topics": ["Strength training", "Nutrition", "Habit building"],
            "status": "active",
            "color": "#0ea5e9",
            "owner": users["maya"]
        },
        {
            "id_str": "verdant",
            "name": "Verdant Home",
            "domain": "verdanthome.co",
            "url": "https://verdanthome.co",
            "industry": "Home & Garden",
            "tone": "Calm, informative",
            "topics": ["Houseplants", "Sustainable living", "Decor"],
            "status": "active",
            "color": "#16a34a",
            "owner": users["aisha"]
        },
        {
            "id_str": "fintrack",
            "name": "FinTrack",
            "domain": "fintrack.io",
            "url": "https://fintrack.io",
            "industry": "Fintech / SaaS",
            "tone": "Authoritative, clear",
            "topics": ["Personal finance", "Investing", "Budgeting"],
            "status": "paused",
            "color": "#4f46e5",
            "owner": users["marcus"]
        },
        {
            "id_str": "atlas",
            "name": "Atlas Travel",
            "domain": "atlastravel.com",
            "url": "https://atlastravel.com",
            "industry": "Travel",
            "tone": "Adventurous, vivid",
            "topics": ["City guides", "Budget travel", "Hidden gems"],
            "status": "active",
            "color": "#db2777",
            "owner": users["aisha"]
        },
        {
            "id_str": "bloom",
            "name": "Bloom Skincare",
            "domain": "bloomskin.co",
            "url": "https://bloomskin.co",
            "industry": "Beauty",
            "tone": "Friendly, science-led",
            "topics": ["Skincare routines", "Ingredients", "Self-care"],
            "status": "draft",
            "color": "#e11d48",
            "owner": users["marcus"]
        }
    ]
    
    websites = {}
    for wd in websites_data:
        id_str = wd.pop("id_str")
        w = Website.objects.create(**wd)
        websites[id_str] = w
        
        # Add social connections
        for platform, handle in [("linkedin", "company/" + id_str), ("youtube", "@" + id_str), ("blog", wd["domain"] + "/feed")]:
            SocialConnection.objects.create(
                website=w,
                platform=platform,
                make_webhook_url="https://hook.us1.make.com/demo"
            )
            
    print("Creating content drafts...")
    content_data = [
        {
            "site": "northwind",
            "platform": "blog",
            "title": "The Complete Guide to Pour-Over Coffee at Home",
            "status": "draft",
            "body": "Pour-over coffee rewards patience. The method looks simple — hot water, ground coffee, a paper filter — but three variables quietly decide whether your cup is bright and aromatic or flat and bitter.\n\nThe first is grind size. Too fine and water struggles through, over-extracting into bitterness; too coarse and it rushes past, leaving a thin, sour brew. Aim for the texture of coarse sea salt.\n\nThe second is the bloom. Pour just enough water to saturate the grounds, then wait thirty seconds as trapped CO₂ escapes. This single pause is the difference between amateur and café-quality.",
            "excerpt": "Pour-over coffee rewards patience. In this guide we walk through grind size, water temperature, and the bloom — the three levers that separate a flat cup from a bright, aromatic one…",
            "day": "Mon",
            "time": "09:00"
        },
        {
            "site": "northwind",
            "platform": "instagram",
            "title": "5 signs your beans are past their prime",
            "status": "approved",
            "body": "Stale beans? Here's how to tell 👇 Flat aroma, no bloom, oily surface, dull color, sour finish. Tag a friend who needs a fresh bag ☕️ #specialtycoffee #pourover #coffeelover",
            "excerpt": "Stale beans? Here's how to tell 👇 Flat aroma, no bloom, oily surface, dull color, sour finish. Tag a friend who needs a fresh bag ☕️",
            "day": "Tue",
            "time": "12:30"
        },
        {
            "site": "lumen",
            "platform": "linkedin",
            "title": "Why 'progressive overload' beats motivation every time",
            "status": "scheduled",
            "body": "Motivation is a terrible training partner. It shows up when conditions are perfect and ghosts you in February. Progressive overload doesn't care how you feel — it just asks for slightly more than last week.\n\nAdd 2.5kg. One more rep. A few seconds longer under tension. Boring? Yes. Effective? Relentlessly.",
            "excerpt": "Motivation is a terrible training partner. It shows up when conditions are perfect and ghosts you in February. Progressive overload doesn't care how you feel…",
            "day": "Wed",
            "time": "08:00"
        },
        {
            "site": "atlas",
            "platform": "youtube",
            "title": "Lisbon in 48 hours — the locals' itinerary",
            "status": "published",
            "body": "Skip the tourist traps. This 48-hour Lisbon guide covers the miradouros, the best pastéis de nata, and a sunset spot the guidebooks miss.",
            "excerpt": "Skip the tourist traps. This 48-hour Lisbon guide covers the miradouros, the best pastéis de nata, and a sunset spot the guidebooks miss.",
            "day": "Thu",
            "time": "17:00"
        },
        {
            "site": "verdant",
            "platform": "blog",
            "title": "7 Low-Light Houseplants That Actually Thrive",
            "status": "draft",
            "body": "Not every home is flooded with sunlight, and that's fine. These seven plants evolved on shaded forest floors and ask for very little…",
            "excerpt": "Not every home is flooded with sunlight, and that's fine. These seven plants evolved on shaded forest floors and ask for very little…",
            "day": "Fri",
            "time": "10:00"
        },
        {
            "site": "lumen",
            "platform": "instagram",
            "title": "The 3-move kettlebell finisher",
            "status": "approved",
            "body": "Got 6 minutes? Swings × 15, goblet squats × 12, push press × 10. Three rounds. Save this for leg day 🔥",
            "excerpt": "Got 6 minutes? Swings × 15, goblet squats × 12, push press × 10. Three rounds. Save this for leg day 🔥",
            "day": "Fri",
            "time": "18:00"
        },
        {
            "site": "atlas",
            "platform": "linkedin",
            "title": "What 12 months of slow travel taught our team about content",
            "status": "scheduled",
            "body": "A year ago we swapped two big trips for twelve small ones. The content lessons surprised us more than the travel ones…",
            "excerpt": "A year ago we swapped two big trips for twelve small ones. The content lessons surprised us more than the travel ones…",
            "day": "Sat",
            "time": "11:00"
        },
        {
            "site": "fintrack",
            "platform": "blog",
            "title": "Sinking Funds: the budgeting trick that ends 'surprise' expenses",
            "status": "draft",
            "body": "Car registration. Holidays. The annual insurance hit. None of these are surprises — yet they wreck budgets every year. Sinking funds fix that…",
            "excerpt": "Car registration. Holidays. The annual insurance hit. None of these are surprises — yet they wreck budgets every year. Sinking funds fix that…",
            "day": "Mon",
            "time": "07:30"
        },
        {
            "site": "northwind",
            "platform": "youtube",
            "title": "Roasting at home: light vs. medium vs. dark",
            "status": "draft",
            "body": "We roasted the same Ethiopian beans three ways so you don't have to guess. Here's what changes in the cup at each level.",
            "excerpt": "We roasted the same Ethiopian beans three ways so you don't have to guess. Here's what changes in the cup at each level.",
            "day": "Wed",
            "time": "15:00"
        },
        {
            "site": "verdant",
            "platform": "instagram",
            "title": "Repotting 101 in one carousel",
            "status": "published",
            "body": "Roots circling the pot? It's time. Swipe for the 4-step repot that won't shock your plant 🌱",
            "excerpt": "Roots circling the pot? It's time. Swipe for the 4-step repot that won't shock your plant 🌱",
            "day": "Tue",
            "time": "13:00"
        },
        {
            "site": "atlas",
            "platform": "blog",
            "title": "The underrated European cities for a winter break",
            "status": "approved",
            "body": "Everyone flocks to the same five cities. Meanwhile Ljubljana, Porto, and Tallinn sit half-empty under string lights…",
            "excerpt": "Everyone flocks to the same five cities. Meanwhile Ljubljana, Porto, and Tallinn sit half-empty under string lights…",
            "day": "Thu",
            "time": "09:30"
        },
        {
            "site": "lumen",
            "platform": "blog",
            "title": "How much protein do you actually need? A no-hype breakdown",
            "status": "draft",
            "body": "The internet says everything from 0.8g to 2.2g per kg. Here's what the research actually supports for everyday lifters…",
            "excerpt": "The internet says everything from 0.8g to 2.2g per kg. Here's what the research actually supports for everyday lifters…",
            "day": "Sat",
            "time": "10:30"
        }
    ]

    day_offsets = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}

    for cd in content_data:
        site_str = cd.pop("site")
        w = websites[site_str]
        
        # Create ContentIdea
        idea = ContentIdea.objects.create(
            website=w,
            submitted_by=w.owner,
            title=cd["title"],
            platform=cd["platform"],
            status="done"
        )
        
        # Create ContentDraft
        draft = ContentDraft.objects.create(
            idea=idea,
            website=w,
            platform=cd["platform"],
            title=cd["title"],
            body=cd["body"],
            excerpt=cd["excerpt"],
            status=cd["status"]
        )
        
        # If scheduled or published, create ScheduledPost
        if cd["status"] in ["scheduled", "published"]:
            # Calculate a date in this week
            today_date = timezone.now().date()
            start_of_week = today_date - timedelta(days=today_date.weekday()) # Monday
            scheduled_date = start_of_week + timedelta(days=day_offsets[cd["day"]])
            scheduled_time = timezone.datetime.strptime(cd["time"], "%H:%M").time()
            scheduled_datetime = timezone.make_aware(
                timezone.datetime.combine(scheduled_date, scheduled_time)
            )
            
            ScheduledPost.objects.create(
                draft=draft,
                scheduled_for=scheduled_datetime,
                is_published=(cd["status"] == "published"),
                published_at=scheduled_datetime if (cd["status"] == "published") else None
            )

    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed()
