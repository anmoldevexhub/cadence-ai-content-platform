import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from websites.models import ScrapeResult
import re

for p in ScrapeResult.objects.all():
    title = p.page_title.strip()
    if not title:
        continue
    delimiters = r'[:\?|,\.]|\b(?:help|achieve|for|in|on|with|by|and|to|is|are|the|how|why|about)\b'
    parts = re.split(delimiters, title, flags=re.IGNORECASE)
    
    stop_words = {'how', 'why', 'the', 'a', 'an', 'what', 'is', 'are', 'about', 'to', 'for', 'in', 'on', 'with', 'by'}
    extracted_parts = []
    for part in parts:
        p_clean = part.strip()
        while True:
            words = p_clean.split()
            if words and words[0].lower() in stop_words:
                words = words[1:]
                p_clean = " ".join(words)
            else:
                break
        if p_clean:
            extracted_parts.append(p_clean)
            
    title_parts = [title] + extracted_parts
    raw_keywords = title_parts + [tag for tag in (p.categories_tags or []) if tag]
    
    common_generic = {
        'differences', 'difference', 'digital', 'marketing', 'online', 'simple', 'steps', 
        'immune', 'health', 'sleep', 'doctor', 'doctors', 'career', 'skills', 'balance', 
        'tutors', 'teachers', 'nature', 'brief', 'guide', 'future', 'efficiency', 'innovation',
        'support', 'impact', 'device', 'devices', 'unlocked', 'unleashed', 'diagnostics',
        'complexity', 'businesses', 'automation', 'understanding', 'business', 'process'
    }
    keywords = []
    for kw in raw_keywords:
        kw_clean = kw.strip()
        if not kw_clean:
            continue
        word_count = len(kw_clean.split())
        if word_count >= 2:
            keywords.append(kw_clean)
        elif len(kw_clean) >= 6 and kw_clean.lower() not in common_generic:
            keywords.append(kw_clean)
            
    # Print if any keyword matches "answers" or "answer"
    if any(k.lower() == 'answers' or k.lower() == 'answer' for k in keywords):
        print(f"MATCH: {title} | URL: {p.page_url}")
        print("  Keywords:", keywords)
