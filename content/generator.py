"""
OpenAI-powered content generation.
Uses gpt-4o-mini (cheapest capable model).
"""
import logging
from openai import OpenAI
from decouple import config

from websites.models import Website, ScrapeResult
from .models import ContentIdea, ContentDraft

logger = logging.getLogger(__name__)
client = OpenAI(api_key=config('OPENAI_API_KEY'))

MODEL = 'gpt-4o-mini'   # cheapest OpenAI model, ~$0.15/1M input tokens


def summarize_website_style(structure_text: str) -> str:
    """
    Called after crawl. Returns a concise style guide for the website.
    Stored in Website.scrape_summary for reuse in all future generation.
    """
    prompt = f"""Analyze this website structure and extract:
1. Writing tone (formal/casual/technical/conversational)
2. Typical blog post structure (intro pattern, heading style, CTAs, length)
3. Key topics and recurring themes
4. Vocabulary / brand voice markers
5. Any SEO patterns observed

Website structure:
{structure_text[:6000]}

Return a concise style guide (under 400 words) that an AI writer should follow 
when creating content for this website. Be specific and actionable."""
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=600,
        temperature=0.3,
    )
    return response.choices[0].message.content


def build_system_prompt(website: Website) -> str:
    """Builds the persistent system prompt for content generation, including detailed style guide if present."""
    style_details = ""
    extra_instructions = []
    
    if website.style_guide:
        import json
        try:
            guide = website.style_guide if isinstance(website.style_guide, dict) else json.loads(website.style_guide)
            parts = []
            for key, val in guide.items():
                if key not in {'average_grade_level', 'average_sentiment_polarity', 'call_to_action_examples'}:
                    parts.append(f"- {key}: {val}")
            style_details = "\n" + "\n".join(parts)
            
            # Extract readability metrics
            grade_level = guide.get('average_grade_level')
            if grade_level is not None:
                extra_instructions.append(f"- Target Reading Level: Write at approximately a {grade_level}th-grade reading level.")
                
            # Extract sentiment metrics
            sentiment = guide.get('average_sentiment_polarity')
            if sentiment is not None:
                sentiment_val = float(sentiment)
                if sentiment_val > 0.15:
                    tone_desc = "slightly positive and optimistic"
                elif sentiment_val < -0.15:
                    tone_desc = "slightly critical or analytical"
                else:
                    tone_desc = "neutral and balanced"
                extra_instructions.append(f"- Sentiment: Maintain a {tone_desc} tone (average sentiment polarity: {sentiment_val}).")
                
            # Extract CTA metrics
            ctas = guide.get('call_to_action_examples')
            if ctas:
                ctas_str = ", ".join([f"'{c}'" for c in ctas[:3]])
                extra_instructions.append(f"- Calls to Action: Naturally include one of these common CTAs where appropriate: {ctas_str}.")
        except Exception:
            style_details = "\n" + str(website.style_guide)
            
    extra_instructions_str = "\n".join(extra_instructions)
    if extra_instructions_str:
        extra_instructions_str = "\n\nWRITING METRICS & CONSTRAINTS:\n" + extra_instructions_str
        
    return f"""You are an expert content writer for {website.name} ({website.domain}).

WEBSITE STYLE GUIDE:
{website.scrape_summary or "No style guide available yet. Write in an engaging, human tone."}{style_details}{extra_instructions_str}

BRAND VOICE: {website.tone or "Conversational and engaging"}
KEY TOPICS: {", ".join(website.topics) if website.topics else "General content"}
INDUSTRY: {website.industry or "General"}

When writing blog posts:
- Always write a detailed, comprehensive, deep-dive article of at least 900 to 1200 words. Do not stop until you have covered the topic in full depth.
- Avoid brief outlines or summaries. Write in simple, everyday English (no corporate jargon or complex AI words).
- Vary sentence lengths dramatically. Use very short, punchy sentences alongside longer, conversational ones.
- Avoid perfectly symmetrical section structures. Make layout, section length, and bullet points uneven and varied.
- Never break character or mention that you are an AI."""


def search_live_data(query: str) -> str:
    """
    Searches DuckDuckGo HTML for query and extracts snippet descriptions.
    """
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import quote_plus

    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    }
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        snippets = []
        for i, a in enumerate(soup.find_all('a', class_='result__snippet')[:4], 1):
            text = a.get_text(strip=True)
            if text:
                snippets.append(f"[{i}] {text}")
        if snippets:
            return "\n".join(snippets)
    except Exception as e:
        logger.warning(f"Live DDG search failed for query '{query}': {e}")
    return "No live data available."


def get_rich_fallback_blog(title: str) -> dict:
    t_lower = title.lower()
    
    if "python" in t_lower:
        body = """<h2>How Python Looks Today in 2026</h2>
<p>If you want to learn to code, you have probably heard that Python is a great first choice. But in 2026, the way we learn and write code is different than before. With new AI helper tools and new ways to run code, you cannot just watch old video tutorials from a few years ago. Learning Python today is not about memorizing commands. It is about learning how to solve real problems and building things that work well.</p>

<h2>Here is My Unpopular Opinion about Tutorials</h2>
<p>Most coding tutorials are a complete waste of time. Yes, really. They make you feel like you are learning, but you are actually just copying someone else's screen. I call it the tutorial trap. The best way to learn is to write bad, broken code that fails. You learn when things go wrong, not when they go right.</p>

<h2>My 2-Hour Coding Failure</h2>
<p>We all make stupid mistakes. Just last week, I spent 2 hours debugging because I made a tiny error. I was trying to activate my Python environment on Windows and typed a path wrong. I kept typing <code>venv/bin/activate</code> instead of <code>venv/Scripts/activate</code> because I was looking at a Mac tutorial. The terminal just kept saying "path not found" and I was pulling my hair out. I felt so silly when I finally realized. But guess what? I will never make that mistake again. That is how learning actually happens.</p>

<h2>Some Python Statistics for 2026</h2>
<p>If you wonder why Python is still worth your time, look at these numbers from early 2026 developer surveys:</p>
<table border="1" style="border-collapse: collapse; width: 100%; text-align: left; margin: 15px 0;">
  <thead>
    <tr style="background-color: #f2f2f2;">
      <th style="padding: 8px;">Use Case</th>
      <th style="padding: 8px;">Share of Developers</th>
      <th style="padding: 8px;">Popularity Growth (YoY)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 8px;">Machine Learning & AI</td>
      <td style="padding: 8px;">68%</td>
      <td style="padding: 8px;">+14%</td>
    </tr>
    <tr>
      <td style="padding: 8px;">Web Development (FastAPI/Django)</td>
      <td style="padding: 8px;">42%</td>
      <td style="padding: 8px;">+5%</td>
    </tr>
    <tr>
      <td style="padding: 8px;">Simple Automation & Scripts</td>
      <td style="padding: 8px;">55%</td>
      <td style="padding: 8px;">+8%</td>
    </tr>
  </tbody>
</table>

<h2>How to Use AI Without Cheating Yourself</h2>
<p>We have AI tools like ChatGPT now. They are great. But if you just ask AI to write all your code, you will learn absolutely nothing. Use AI like a teacher. When you get a weird error message, paste it in. Ask the AI: "Explain this error like I am ten years old." That is a smart way to use it.</p>

<h2>Common Questions & Answers</h2>
<p><strong>Q: Is Python too slow for real business apps?</strong><br>
A: No. While it is slower than C++ or Go, it is fast enough for 95% of websites. Instagram runs on Python. If it works for them, it works for your project.</p>
<p><strong>Q: How many hours should I study each day?</strong><br>
A: Don't study for hours. Just write code for 30 minutes a day. Consistency is much better than trying to cram everything in on weekends.</p>

<h2>Conclusion</h2>
<p>Do not wait until you feel "ready" to start coding. Set up Python, write a simple script that prints your name, and break it on purpose. Have fun with the errors!</p>"""
        
        return {
            "title": "How to Learn Python in 2026: A Simple Guide",
            "meta_description": "Learn Python in 2026 with this simple guide. Start with small projects, use AI tools to learn, and find out about the best libraries for beginners.",
            "category": "Web Development",
            "tags": ["Python", "Learn to Code", "Programming", "Beginner Guide"],
            "excerpt": "A simple guide to learning Python in 2026. Discover how to write your first programs, use helpful AI tools, and avoid common coding mistakes.",
            "body": body
        }
        
    elif "hospitality" in t_lower or "hotel" in t_lower:
        body = """<h2>How Smart Tech is Changing Hotels</h2>
<p>The hotel business is changing fast. Today, guests want things to be fast and easy. That is why hotels are installing smart systems. But wait. Is all this tech actually good?</p>

<h2>An Unpopular Opinion: Guests Hate "Smart" Rooms</h2>
<p>Here is my honest view. Most guests do not want a room where they have to download an app just to turn off the bedside lamp. They want simple, physical switches. When a hotel room gets too complicated, guests get annoyed. The best smart hotels keep technology invisible. The lights should just turn off when you want them to, without an iPad.</p>

<h2>My Thermostat Failure Story</h2>
<p>I learned this the hard way. I was helping a small hotel set up their new smart climate control. I spent 2 hours debugging because guests kept complaining that their rooms were freezing. The system was showing 18 degrees. I thought it was 18 Celsius (which is about 64 Fahrenheit), but the thermostat thought it was 18 Fahrenheit! The API didn't handle unit conversions properly. It was a stupid mistake that made guest stays miserable for a night. I had to manually rewrite the config file to fix it.</p>

<h2>Guest Preferences in 2026</h2>
<p>Here are the latest survey results showing what hotel guests actually care about when it comes to technology:</p>
<table border="1" style="border-collapse: collapse; width: 100%; text-align: left; margin: 15px 0;">
  <thead>
    <tr style="background-color: #f2f2f2;">
      <th style="padding: 8px;">Technology Feature</th>
      <th style="padding: 8px;">Guest Preference Rate</th>
      <th style="padding: 8px;">Perceived Value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 8px;">High-Speed Wi-Fi (Free)</td>
      <td style="padding: 8px;">94%</td>
      <td style="padding: 8px;">Essential</td>
    </tr>
    <tr>
      <td style="padding: 8px;">Mobile Keyless Entry</td>
      <td style="padding: 8px;">62%</td>
      <td style="padding: 8px;">Convenient</td>
    </tr>
    <tr>
      <td style="padding: 8px;">Voice-Activated Room Controls</td>
      <td style="padding: 8px;">24%</td>
      <td style="padding: 8px;">Gimmick</td>
    </tr>
  </tbody>
</table>

<h2>Keeping the Human Element</h2>
<p>Technology should make staff faster, not replace them. A kiosk can check you in, but it cannot recommend the best local spot for dinner. The goal is to automate paperwork so staff can focus on the guest.</p>

<h2>Common Questions & Answers</h2>
<p><strong>Q: Do smart keys work if my phone battery dies?</strong><br>
A: Usually, no. That is why hotels always keep physical backup cards at the front desk. Always grab one just in case.</p>
<p><strong>Q: Are smart hotels safe from hackers?</strong><br>
A: They can be, but hotels must invest in good security. If a hotel does not update its software, hacker attacks can happen.</p>

<h2>Conclusion</h2>
<p>Smart hotels are the future, but only if they keep things simple. Technology should help the guest, not confuse them.</p>"""
        
        return {
            "title": "Smart Systems in Hospitality: Redefining Guest Experiences",
            "meta_description": "Learn how smart devices, IoT, and automated services are transforming guest comfort and operations in modern hotels.",
            "category": "Technology",
            "tags": ["Hotels", "Smart Tech", "Guest Experience", "Automation"],
            "excerpt": "A simple guide to how technology is changing hotels. Learn how smart rooms and automation help make guests feel welcome.",
            "body": body
        }
        
    elif "artificial intelligence" in t_lower or "ai" in t_lower:
        body = """<h2>Understanding Artificial Intelligence in Simple Terms</h2>
<p>You probably hear about Artificial Intelligence, or AI, every day. From smart assistants on our phones to systems that predict the weather, AI is all around us. But many people still find it confusing. In simple terms, AI is about making computers perform tasks that usually require human thinking, like understanding language, recognizing faces, or making decisions. Let's look at how it works and how we use it today.</p>

<h2>An Unpopular Opinion: AI is Making Code Worse</h2>
<p>Everyone says AI is going to replace human coders. I disagree. AI is actually making a lot of software worse. Because anyone can now generate code with a prompt, people are copying and pasting things they do not understand. This is leading to bloated, buggy software. AI is not replacing smart coders. It is just helping bad coders write bad code faster.</p>

<h2>The Circular Dependency Nightmare</h2>
<p>I fell into this trap myself. I was lazy and asked an AI to write a database script. I spent 2 hours debugging because the server kept crashing with a memory error. The AI had generated a circular dependency where two functions kept calling each other in an infinite loop. Since I had just copied and pasted it without reading, it took me forever to trace the loop. It taught me a valuable lesson: always read every line of code, even if a smart computer wrote it.</p>

<h2>AI Adoption Across Industries</h2>
<p>Here is how different businesses are adopting AI tools in their daily workflows:</p>
<table border="1" style="border-collapse: collapse; width: 100%; text-align: left; margin: 15px 0;">
  <thead>
    <tr style="background-color: #f2f2f2;">
      <th style="padding: 8px;">Industry</th>
      <th style="padding: 8px;">Adoption Rate</th>
      <th style="padding: 8px;">Primary Use Case</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 8px;">Customer Support</td>
      <td style="padding: 8px;">58%</td>
      <td style="padding: 8px;">Chatbots & Routing</td>
    </tr>
    <tr>
      <td style="padding: 8px;">Software Development</td>
      <td style="padding: 8px;">47%</td>
      <td style="padding: 8px;">Code Autocomplete</td>
    </tr>
    <tr>
      <td style="padding: 8px;">Marketing & Design</td>
      <td style="padding: 8px;">38%</td>
      <td style="padding: 8px;">Content Writing</td>
    </tr>
  </tbody>
</table>

<h2>The Future of AI is Collaborative</h2>
<p>The best results happen when humans and AI work together. AI handles the boring, repetitive work. Humans handle the logic, the design, and the empathy.</p>

<h2>Common Questions & Answers</h2>
<p><strong>Q: Can AI learn on its own like a human?</strong><br>
A: No. AI needs data to learn. It cannot think outside of the examples it has been shown.</p>
<p><strong>Q: Is my data safe with public AI tools?</strong><br>
A: If you paste sensitive information into public chats, it might be used to train the model. Never paste passwords or private customer data.</p>

<h2>Conclusion</h2>
<p>AI is a great helper, but it is not a replacement for human judgment. Use it wisely, check its work, and never copy-paste blindly.</p>"""
        
        return {
            "title": "What is Artificial Intelligence? A Practical Guide",
            "meta_description": "Learn the basics of Artificial Intelligence, including Machine Learning, neural networks, and how we use smart technology in our daily lives.",
            "category": "Artificial Intelligence",
            "tags": ["AI", "Machine Learning", "Technology", "Beginner Guide"],
            "excerpt": "A simple guide to understanding AI and Machine Learning. Find out how computers learn from examples and explore real-world applications.",
            "body": body
        }
        
    else:
        body = f"""<h2>A Simple Guide to {title}</h2>
<p>Understanding <strong>{title}</strong> is very important today. Whether you are learning about it for the first time or looking for new ways to improve, this guide will explain the basics in a simple way.</p>

<h2>An Unpopular Opinion: Stop Making Long Plans</h2>
<p>Most people spend weeks planning a project before starting. I think this is a waste of time. Long plans usually fail because real life is unpredictable. Instead, throw away your calendar and build the most important part first. Figure out the rest as you go.</p>

<h2>My Task-List Failure</h2>
<p>I learned this because I was bad at managing my own work. I once spent 2 hours debugging because I got obsessed with color-coding my project board. I was setting up tags, priorities, and colors instead of doing the actual work. By the time I finished organizing, I was too tired to write any code. It was a complete failure of productivity. Now, I just write my tasks on a plain piece of paper.</p>

<h2>Project Success Statistics</h2>
<p>Here are some interesting stats about how planning affects project completion rates:</p>
<table border="1" style="border-collapse: collapse; width: 100%; text-align: left; margin: 15px 0;">
  <thead>
    <tr style="background-color: #f2f2f2;">
      <th style="padding: 8px;">Planning Method</th>
      <th style="padding: 8px;">On-Time Completion Rate</th>
      <th style="padding: 8px;">Team Satisfaction</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 8px;">Agile (Iterative building)</td>
      <td style="padding: 8px;">74%</td>
      <td style="padding: 8px;">High</td>
    </tr>
    <tr>
      <td style="padding: 8px;">Waterfall (Strict long planning)</td>
      <td style="padding: 8px;">42%</td>
      <td style="padding: 8px;">Low</td>
    </tr>
    <tr>
      <td style="padding: 8px;">No Planning (Ad-hoc)</td>
      <td style="padding: 8px;">31%</td>
      <td style="padding: 8px;">Medium</td>
    </tr>
  </tbody>
</table>

<h2>Steps for Success</h2>
<p>Break down big tasks into small steps. Assign roles clearly, and do not be afraid to change your plan when you get new information.</p>

<h2>Common Questions & Answers</h2>
<p><strong>Q: What should I do if my project feels too big?</strong><br>
A: Focus on just one small thing. Finish it completely before looking at the rest of the project.</p>
<p><strong>Q: How do I know if my plan is working?</strong><br>
A: Check if you are actually producing anything. If you are just moving tasks around on a board, your plan is not working.</p>

<h2>Conclusion</h2>
<p>Keeping things simple is the key to success. Focus on action, learn from your mistakes, and keep moving forward.</p>"""
        
        return {
            "title": f"The Guide to {title}",
            "meta_description": f"Learn the core strategies, implementation steps, and best practices for {title} in this comprehensive and practical guide.",
            "category": "General Business",
            "tags": ["guide", "strategy", "planning", "success"],
            "excerpt": f"A detailed guide to mastering {title}. Explore core principles, step-by-step workflows, trade-offs, and strategies for success.",
            "body": body
        }


def generate_via_gemini(system_prompt: str, user_prompt: str) -> dict:
    """Calls Google Gemini API using requests."""
    import requests
    import json
    
    api_key = config('GEMINI_API_KEY', default=config('GOOGLE_API_KEY', default=None))
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    combined_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": combined_prompt
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "meta_description": {"type": "STRING"},
                    "category": {"type": "STRING"},
                    "tags": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    },
                    "excerpt": {"type": "STRING"},
                    "body": {"type": "STRING"}
                },
                "required": ["title", "meta_description", "category", "tags", "excerpt", "body"]
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    
    try:
        text_content = result['candidates'][0]['content']['parts'][0]['text']
        content = json.loads(text_content.strip())
        content['generation_prompt'] = user_prompt
        content['ai_model'] = 'gemini-1.5-flash'
        return content
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Failed to parse Gemini response: {e}")
        raise ValueError("Invalid response format from Gemini")


def generate_social_via_gemini(system_prompt: str, user_prompt: str) -> dict:
    """Calls Google Gemini API for social media post generation."""
    import requests
    import json
    
    api_key = config('GEMINI_API_KEY', default=config('GOOGLE_API_KEY', default=None))
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    combined_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": combined_prompt
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "body": {"type": "STRING"},
                    "excerpt": {"type": "STRING"},
                    "tags": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    },
                    "meta_description": {"type": "STRING"}
                },
                "required": ["title", "body", "excerpt", "tags", "meta_description"]
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    
    try:
        text_content = result['candidates'][0]['content']['parts'][0]['text']
        content = json.loads(text_content.strip())
        content['generation_prompt'] = user_prompt
        content['ai_model'] = 'gemini-1.5-flash'
        return content
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Failed to parse Gemini response: {e}")
        raise ValueError("Invalid response format from Gemini")


def generate_blog_post(idea: ContentIdea, website: Website) -> dict:
    """Generates a full blog post (HTML-ready) utilizing crawled styles and live search data."""
    system_prompt = build_system_prompt(website)
    
    # Perform live web search to retrieve current facts & context
    logger.info(f"Performing live search for topic: {idea.title}")
    live_data = search_live_data(idea.title)
    
#     user_prompt = f"""Write a complete, authoritative, high-impact, and SEO-optimized blog post for {website.name}.

# TOPIC: {idea.title}
# ADDITIONAL CONTEXT FROM ADMIN: {idea.context or "None provided."}
# TARGET TAGS/KEYWORDS: {", ".join(idea.meta_tags) if idea.meta_tags else "Auto-select relevant keywords"}

# ================================================================================
# LIVE SEARCH DATA (REQUIRED – You MUST use at least 2 specific facts/stats from this):
# ================================================================================
# {live_data}

# ================================================================================
# VOICE & PERSONALITY REQUIREMENTS (CRITICAL – FOLLOW STRICTLY):
# ================================================================================

# You are NOT a neutral content writer. You are a CONFIDENT INDUSTRY CONSULTANT who has seen what works and what doesn't. Take a stance. Don't sit on the fence.

# 1. THE HOOK (First 2-3 sentences):
#    - MUST start with a BOLD, COUNTER-INTUITIVE, or PROVOCATIVE statement.
#    - Use ONE of these hook formulas:
#      a) Metaphor: "Your [topic] is not a [X]. It's more like a [Y] that [does Z]."
#      b) Contradiction: "Most [people/companies] think [common belief]. They couldn't be more wrong."
#      c) Bold Statement: "The [X] you've been told doesn't work. Here's what actually does."
#      d) Vivid Imagery: "Imagine [visual scenario]. That's exactly what [topic] feels like."
#    - ❌ NEVER start with: "Have you ever wondered...", "In today's world...", "In this blog post..."

# 2. BOLD OPINION / CHALLENGING THE STATUS QUO (Conditional):
#    - ONLY include a bold, opinionated section if the topic naturally allows for a debatable stance.
#    - If the topic is purely educational, technical, or news-based, SKIP this section entirely and write a straightforward, informative article.
#    - DO NOT force an opinion into every blog. It looks contrived and repetitive.
#    - If included:
#      * DO NOT use "I think", "I disagree", "Here's my honest take" – this is a COMPANY blog.
#      * Use collective voice: "Our team has found...", "In our experience...", "At {website.name}, we've seen..."
#      * 🔒 IMPORTANT: Weave the opinion naturally into the narrative. Do NOT use a dedicated heading like "Challenging the Status Quo" – it looks forced and repetitive.
#      * Example: "Most companies assume X. Through our work with clients, we've found that Y actually drives better results."
#    - If NOT included: Write a clear, informative, and valuable blog without taking a provocative stance.

# 3. AUTHORITY & DATA:
#    - MUST include at least 2-3 specific statistics, study findings, or data points.
#    - ALWAYS name the source: "According to [Source]...", "[Organization] reports..."
#    - Use the LIVE SEARCH DATA to find recent stats. Weave them into the narrative naturally.

# 4. INDUSTRY-SPECIFIC TERMINOLOGY:
#    - Use the exact terminology that professionals in that industry use.
#    - Use the LIVE SEARCH DATA to find these terms.
#    - NEVER use generic language when specific terms exist.
#    - 🔒 CRITICAL: Do NOT copy terms from examples. Only use terms found in the LIVE SEARCH DATA or the website's own content (topics, industry, style guide).

# 5. DIAGNOSTIC DEPTH:
#    - Don't just say "poor X" – give 3-4 SPECIFIC, ACTIONABLE examples of problems.
#    - For each problem, describe: WHAT happens, WHO it affects, and WHY it matters.
#    - Use the LIVE SEARCH DATA and the website's industry context to find REAL problems people face.
#    - Example format: "[Specific practice/field] is often mishandled. When [specific action] happens repeatedly, [specific negative consequence] occurs."
#    - 🔒 CRITICAL: Do NOT copy generic examples. Generate problems specific to THIS industry and topic from the LIVE SEARCH DATA.

# 6. PUNCHY QUOTES:
#    - Include at least 2-3 short, punchy sentences (under 12 words) throughout the article.
#    - These should be bold, quotable statements that readers will want to share.
#    - Create your OWN punchy lines based on the topic – don't copy from examples.
#    - Formula: Take a key insight from your article and compress it into 6-10 words.
#    - 🔒 IMPORTANT: Do NOT create a dedicated "Punchy Insights" or "Key Takeaways" section. Weave these punchy lines naturally into the narrative – as standalone bold sentences or pull quotes.

# 7. BRAND INTEGRATION:
#    - Mention "{website.name}" naturally as the SOLUTION to the problems you've diagnosed.
#    - The brand mention should feel like a natural next step, not a sales pitch.
#    - GOOD: "At {website.name}, we help [industry] teams [solve specific problem]."
#    - GOOD: "Explore {website.name}'s [specific service] to [solve the specific problem you just diagnosed]."
#    - GOOD: "To talk through what a more reliable [topic] model could look like for your team, reach out to {website.name}."
#    - BAD: "Partner with {website.name} today" – too generic and salesy.

# 8. VOICE & TONE:
#    - Take a stance. Don't sit on the fence. Be provocative when appropriate.
#    - Use short, punchy sentences alongside longer explanations.
#    - Use rhetorical questions to engage readers.
#    - NEVER sound like a textbook, academic paper, or student essay.

# 9. HUMANIFICATION (Make it Feel Real):
#    - Optionally include a short, relatable example of a lesson learned or challenge overcome.
#    - Vary the story EVERY time—do NOT repeat the same phrase across blogs.
#    - ✅ GOOD APPROACHES (adapt to the topic):
#      * Technical/Software: "Our team spent hours troubleshooting because we overlooked a small configuration error..."
#      * Creative/Design: "We once invested time in a concept that looked great but confused our users..."
#      * Strategic/Planning: "We learned this the hard way when we launched without defining clear success metrics..."
#      * Operational/Process: "We had to redo work because different teams used different definitions..."
#    - 🔒 CRITICAL: Use "we" or "our team" – this is a COMPANY blog, not a personal diary.
#    - The story should feel natural to the topic, not forced.
#    - Use contractions (don't, can't, it's) to sound conversational.
#    - Write at a 9th-grade reading level. Simple, everyday language.

# ================================================================================
# STRUCTURE & FORMATTING REQUIREMENTS:
# ================================================================================

# 10. Word Count: Minimum 900 words. Be comprehensive. Write at least 6-8 detailed sections.
#     - Expand each section with thorough explanations, examples, and actionable insights.
#     - Do NOT use filler or fluff – add genuine value, depth, and detail.
#     - For technical topics: include step-by-step explanations.
#     - For strategic topics: include frameworks, processes, or case studies.
#     - For educational topics: include practical tips and real-world applications.
#     - If you're writing under 900 words, you're not being comprehensive enough – ADD MORE SUBSTANCE.

# 11. Headings: Use <h2> for main sections and <h3> for sub-sections. Do NOT use <h1>.

# 12. Short paragraphs: 2-4 sentences each. Vary section lengths and layout styles.

# 13. Bullet points: Use <ul> and <li> for lists of tips, steps, or key points.

# 14. If the website offers multiple distinct services (as seen in the KEY TOPICS), present them as a clear, scannable bulleted list (<ul>) in one of the main sections.

# 15. Table: If the topic relates to statistics, metrics, trends, or growth (including trends/growth in 2026), you MUST include a clean HTML table.

# 16. Q&A SECTION:
#     - Include 4-5 specific questions that actual customers or readers would ask.
#     - Use the live search data to identify common questions people are asking.
#     - Format as Q&A with bold questions and clear, concise answers.

# 17. CONCLUSION & CALL TO ACTION:
#     - Summarize the key takeaway in 1-2 sentences.
#     - End with a SPECIFIC, VALUE-DRIVEN CTA:
#       ✅ "Partner with {website.name} for a free [specific offer] today."
#       ✅ "Contact {website.name} to [solve specific problem]."
#       ✅ "Explore {website.name}'s [specific service] to [achieve specific goal]."
#       ❌ NEVER use generic "Contact us" or "Learn more" – be specific.

# ================================================================================
# SEO & OUTPUT REQUIREMENTS:
# ================================================================================

# 18. Meta Title: Use the same blog title. MUST be between 55 to 60 characters.

# 19. Meta Description: MUST be exactly between 155 and 160 characters.

# 20. Category: Assign the most appropriate professional category (e.g., "Artificial Intelligence", "Web Development", "Digital Marketing", "Business Strategy", "Technology", "Finance", "Health", etc.).

# 21. Tags: Include 4-6 relevant tags/keywords.

# Format Requirements:
# Return ONLY a valid JSON object with these exact keys:
# {{
#   "title": "...(55-60 characters)...",
#   "meta_description": "...(155-160 characters)...",
#   "category": "...",
#   "tags": ["tag1", "tag2", ...],
#   "excerpt": "...(2-3 sentence preview)...",
#   "body": "...(full blog post in plain HTML using <h2>, <h3>, <p>, <ul>, <li>)..."
# }}

# Do NOT include any markdown code block formatting (like ```json ... ```). Return ONLY the raw JSON."""


    user_prompt = f"""Write a complete, authoritative, high-impact, and SEO-optimized blog post for {website.name}.

    TOPIC: {idea.title}
    ADDITIONAL CONTEXT FROM ADMIN: {idea.context or "None provided."}
    TARGET TAGS/KEYWORDS: {", ".join(idea.meta_tags) if idea.meta_tags else "Auto-select relevant keywords"}

    ================================================================================
    LIVE SEARCH DATA (REQUIRED – You MUST use at least 2 specific facts/stats from this):
    ================================================================================
    {live_data}

    ================================================================================
    CRITICAL: USE THE WEBSITE'S STYLE GUIDE
    ================================================================================
    The System Prompt contains the website's style guide (tone, voice, vocabulary, 
    heading patterns, and CTA style) extracted from crawling the website.

    🔒 FOLLOW THIS INSTRUCTION:
    1. The STYLE GUIDE in the System Prompt is your PRIMARY source for writing style.
    2. FOLLOW the System Prompt's style guide STRICTLY – it contains the website's actual voice.
    3. The rules below (VOICE & PERSONALITY REQUIREMENTS) are SECONDARY – they provide structural guidance.
    4. If there's a conflict, ALWAYS follow the System Prompt's style guide first.
    5. This ensures EVERY blog matches the website's UNIQUE writing style.

    YOU ARE WRITING FOR: {website.name}
    THEIR INDUSTRY: {website.industry}
    THEIR TOPICS: {", ".join(website.topics) if website.topics else "General content"}
    ================================================================================

    ================================================================================
    VOICE & PERSONALITY REQUIREMENTS (CRITICAL – FOLLOW STRICTLY):
    ================================================================================

    You are NOT a neutral content writer. You are a CONFIDENT INDUSTRY CONSULTANT who has seen what works and what doesn't. Take a stance. Don't sit on the fence.

    1. THE HOOK (First 2-3 sentences):
    - MUST start with a BOLD, COUNTER-INTUITIVE, or PROVOCATIVE statement.
    - Use ONE of these hook formulas:
        a) Metaphor: "Your [topic] is not a [X]. It's more like a [Y] that [does Z]."
        b) Contradiction: "Most [people/companies] think [common belief]. They couldn't be more wrong."
        c) Bold Statement: "The [X] you've been told doesn't work. Here's what actually does."
        d) Vivid Imagery: "Imagine [visual scenario]. That's exactly what [topic] feels like."
    - ❌ NEVER start with: "Have you ever wondered...", "In today's world...", "In this blog post..."

    2. BOLD OPINION / CHALLENGING THE STATUS QUO (Conditional):
    - ONLY include a bold, opinionated section if the topic naturally allows for a debatable stance.
    - If the topic is purely educational, technical, or news-based, SKIP this section entirely and write a straightforward, informative article.
    - DO NOT force an opinion into every blog. It looks contrived and repetitive.
    - If included:
        * DO NOT use "I think", "I disagree", "Here's my honest take" – this is a COMPANY blog.
        * Use collective voice: "Our team has found...", "In our experience...", "At {website.name}, we've seen..."
        * 🔒 IMPORTANT: Weave the opinion naturally into the narrative. Do NOT use a dedicated heading like "Challenging the Status Quo" – it looks forced and repetitive.
        * Example: "Most companies assume X. Through our work with clients, we've found that Y actually drives better results."
    - If NOT included: Write a clear, informative, and valuable blog without taking a provocative stance.

    3. AUTHORITY & DATA:
    - MUST include at least 2-3 specific statistics, study findings, or data points.
    - ALWAYS name the source: "According to [Source]...", "[Organization] reports..."
    - Use the LIVE SEARCH DATA to find recent stats. Weave them into the narrative naturally.

    4. INDUSTRY-SPECIFIC TERMINOLOGY:
    - Use the exact terminology that professionals in that industry use.
    - Use the LIVE SEARCH DATA to find these terms.
    - NEVER use generic language when specific terms exist.
    - 🔒 CRITICAL: Do NOT copy terms from examples. Only use terms found in the LIVE SEARCH DATA or the website's own content (topics, industry, style guide).

    5. DIAGNOSTIC DEPTH:
    - Don't just say "poor X" – give 3-4 SPECIFIC, ACTIONABLE examples of problems.
    - For each problem, describe: WHAT happens, WHO it affects, and WHY it matters.
    - Use the LIVE SEARCH DATA and the website's industry context to find REAL problems people face.
    - Example format: "[Specific practice/field] is often mishandled. When [specific action] happens repeatedly, [specific negative consequence] occurs."
    - 🔒 CRITICAL: Do NOT copy generic examples. Generate problems specific to THIS industry and topic from the LIVE SEARCH DATA.

    6. PUNCHY QUOTES:
    - Include at least 2-3 short, punchy sentences (under 12 words) throughout the article.
    - These should be bold, quotable statements that readers will want to share.
    - Create your OWN punchy lines based on the topic – don't copy from examples.
    - Formula: Take a key insight from your article and compress it into 6-10 words.
    - 🔒 IMPORTANT: Do NOT create a dedicated "Punchy Insights" or "Key Takeaways" section. Weave these punchy lines naturally into the narrative – as standalone bold sentences or pull quotes.

    7. BRAND INTEGRATION:
    - Mention "{website.name}" naturally as the SOLUTION to the problems you've diagnosed.
    - The brand mention should feel like a natural next step, not a sales pitch.
    - GOOD: "At {website.name}, we help [industry] teams [solve specific problem]."
    - GOOD: "Explore {website.name}'s [specific service] to [solve the specific problem you just diagnosed]."
    - GOOD: "To talk through what a more reliable [topic] model could look like for your team, reach out to {website.name}."
    - BAD: "Partner with {website.name} today" – too generic and salesy.

    8. VOICE & TONE:
    - Take a stance. Don't sit on the fence. Be provocative when appropriate.
    - Use short, punchy sentences alongside longer explanations.
    - Use rhetorical questions to engage readers.
    - NEVER sound like a textbook, academic paper, or student essay.

    9. HUMANIFICATION (Make it Feel Real):
    - Optionally include a short, relatable example of a lesson learned or challenge overcome.
    - Vary the story EVERY time—do NOT repeat the same phrase across blogs.
    - ✅ GOOD APPROACHES (adapt to the topic):
        * Technical/Software: "Our team spent hours troubleshooting because we overlooked a small configuration error..."
        * Creative/Design: "We once invested time in a concept that looked great but confused our users..."
        * Strategic/Planning: "We learned this the hard way when we launched without defining clear success metrics..."
        * Operational/Process: "We had to redo work because different teams used different definitions..."
    - 🔒 CRITICAL: Use "we" or "our team" – this is a COMPANY blog, not a personal diary.
    - The story should feel natural to the topic, not forced.
    - Use contractions (don't, can't, it's) to sound conversational.
    - Write at a 9th-grade reading level. Simple, everyday language.


   ================================================================================
STRUCTURE & FORMATTING: MATCH THE WEBSITE'S ACTUAL PATTERN
================================================================================

10. CRITICAL: FOLLOW THE WEBSITE'S STRUCTURAL PATTERN (WITH EXAMPLE)

    The website's style guide shows they use THIS EXACT PATTERN:

    ✅ CORRECT PATTERN (Follow this):
    <h2>Heading Here</h2>
    <p>Opening paragraph explaining the concept in 2-3 sentences.</p>
    <p><strong>Key point or benefit in bold</strong> followed by the explanation in regular text. This is how they emphasize important concepts without using bullet points. Every subpoint is written inside a paragraph with bold text for emphasis.</p>
    <p>Another paragraph continuing the explanation. <strong>Another bold key phrase</strong> with the explanation following naturally. The entire section flows as narrative text, not as a list.</p>

    ❌ WRONG PATTERN (DO NOT use):
    <h2>Heading Here</h2>
    <p>Some text...</p>
    <ul>
      <li><strong>Subpoint 1</strong>: Explanation...</li>
      <li><strong>Subpoint 2</strong>: Explanation...</li>
    </ul>

    🔒 INSTRUCTION:
    - NEVER use <ul> or <li> for subpoints.
    - NEVER use numbered lists for benefits or features.
    - ALWAYS use <strong> inside <p> tags for key phrases.
    - ALWAYS write in flowing paragraphs.
    - Match the exact pattern above – it's what the website uses.

11. Word Count: MUST be between 900 and 1200 words.
    - Expand each section with thorough explanations, examples, and reasoning.
    - Write at least 6-8 detailed sections.
    - Each section should have 3-5 paragraphs.

12. Paragraph Structure:
    - Write in complete paragraphs (3-5 sentences each).
    - Use bold text (<strong>) for key phrases, benefits, or takeaways.
    - Let the text flow naturally from one concept to the next.
    - Do NOT use bullet points anywhere.

13. Q&A SECTION:
    - Include 3-4 questions that actual customers or readers would ask.
    - Format as Q&A with bold questions and clear, concise answers in paragraph form.

14. CONCLUSION & CALL TO ACTION:
    - Summarize the key takeaway in 1-2 paragraphs.
    - End with a SPECIFIC, VALUE-DRIVEN CTA in paragraph form.

15. Formatting Rules:
    - Use <h2> for main section headings.
    - Use <p> for all paragraphs.
    - Use <strong> for bold text inside paragraphs.
    - DO NOT use <ul>, <ol>, or <li> anywhere in the article.

    ================================================================================
    SEO & OUTPUT REQUIREMENTS:
    ================================================================================

    18. Meta Title: Use the same blog title. MUST be between 55 to 60 characters.

    19. Meta Description: MUST be exactly between 155 and 160 characters.

    20. Category: Assign the most appropriate professional category (e.g., "Artificial Intelligence", "Web Development", "Digital Marketing", "Business Strategy", "Technology", "Finance", "Health", etc.).

    21. Tags: Include 4-6 relevant tags/keywords.

    Format Requirements:
    Return ONLY a valid JSON object with these exact keys:
    {{
    "title": "...(55-60 characters)...",
    "meta_description": "...(155-160 characters)...",
    "category": "...",
    "tags": ["tag1", "tag2", ...],
    "excerpt": "...(2-3 sentence preview)...",
    "body": "...(full blog post in plain HTML using <h2>, <h3>, <p>, <ul>, <li>)..."
    }}

    Do NOT include any markdown code block formatting (like ```json ... ```). Return ONLY the raw JSON."""
    try:
        # Call OpenAI directly (no Gemini check)
        response = client.chat.completions.create(
            model=MODEL,  # 'gpt-4o-mini'
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            max_tokens=2000,
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        
        import json
        content = json.loads(response.choices[0].message.content)
        content['generation_prompt'] = user_prompt
        content['ai_model'] = MODEL
        return content
    except Exception as e:
        logger.warning(f"AI content generation failed: {e}. Falling back to rich local template.")
        fallback_content = get_rich_fallback_blog(idea.title)
        fallback_content['generation_prompt'] = user_prompt
        fallback_content['ai_model'] = 'local-fallback'
        return fallback_content


def generate_social_post(idea: ContentIdea, website: Website, platform: str) -> dict:
    """Generates platform-specific social media content."""
    limits = {
        'instagram': 'Under 150 words. Casual, emoji-rich, 3-5 hashtags.',
        'linkedin': 'Under 200 words. Professional tone. No emojis. Hook first line.',
        'facebook': 'Under 120 words. Conversational. Include a question to drive comments.',
        'youtube': 'Video description: 150-200 words. Include timestamps section and subscribe CTA.',
        'twitter': 'Under 280 characters. Punchy. One insight.',
    }
    
    instructions = limits.get(platform, 'Under 200 words, platform-appropriate.')
    system_prompt = build_system_prompt(website)
    
    user_prompt = f"""Write a {platform.title()} post for {website.name}.

TOPIC: {idea.title}
ADMIN CONTEXT: {idea.context or "None"}
FORMAT RULES: {instructions}

Return JSON:
{{
  "title": "...(internal label)...",
  "body": "...(the actual post text)...",
  "excerpt": "...(same as body for social)...",
  "tags": ["hashtag1", "hashtag2"],
  "meta_description": ""
}}

Return ONLY the JSON."""

    try:
        # Call OpenAI directly (no Gemini check)
        response = client.chat.completions.create(
            model=MODEL,  # 'gpt-4o-mini'
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            max_tokens=600,
            temperature=0.8,
            response_format={"type": "json_object"},
        )
        
        import json
        content = json.loads(response.choices[0].message.content)
        content['generation_prompt'] = user_prompt
        content['ai_model'] = MODEL
        return content
    except Exception as e:
        logger.warning(f"AI social post generation failed: {e}. Falling back to basic template.")
        content = {
            "title": idea.title,
            "body": f"🚀 Exploring {idea.title}! Consistent content is key to building a strong digital presence. What are your thoughts on this? 👇 #cadence #contentmarketing #ai",
            "excerpt": f"🚀 Exploring {idea.title}! Consistent content is key to building a strong digital presence. What are your thoughts on this? 👇 #cadence #contentmarketing #ai",
            "tags": ["content", "ai"],
            "meta_description": "",
            "generation_prompt": user_prompt,
            "ai_model": "local-fallback"
        }
        return content


def wrap_text(text: str, max_chars: int) -> list:
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    for word in words:
        if current_length + len(word) + 1 > max_chars:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word) + 1
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def build_footer_svg(phone, domain, email, theme_color) -> str:
    footer_items = []
    if phone:
        footer_items.append(('phone', phone))
    if domain:
        footer_items.append(('domain', domain))
    if email:
        footer_items.append(('email', email))
        
    n = len(footer_items)
    if n == 3:
        x_coords = [180, 520, 860]
    elif n == 2:
        x_coords = [320, 720]
    elif n == 1:
        x_coords = [520]
    else:
        return ""
        
    lines = []
    for i, (itype, val) in enumerate(footer_items):
        x = x_coords[i]
        icon_svg = ""
        if itype == 'phone':
            icon_svg = f"""<circle cx="-15" cy="-5" r="12" fill="{theme_color}"/>
      <path d="M -19.5 -8.5 C -19.5 -5 -15 -0.5 -11.5 -0.5 C -10 -0.5 -9.5 -2 -10.5 -3 L -12 -4.5 C -12.5 -5 -13.5 -5 -14 -4.5 L -15 -3.5 C -16 -4 -17 -5 -17.5 -6 L -16.5 -7 C -16 -7.5 -16 -8.5 -16.5 -9 L -18 -10.5 C -19 -11.5 -19.5 -10 -19.5 -8.5 Z" fill="#ffffff"/>"""
        elif itype == 'domain':
            icon_svg = f"""<circle cx="-15" cy="-5" r="12" fill="{theme_color}"/>
      <circle cx="-15" cy="-5" r="7" fill="none" stroke="#ffffff" stroke-width="1.5"/>
      <path d="M -22 -5 L -8 -5 M -15 -12 L -15 2 M -19 -8 Q -15 -5 -11 -8 M -19 -2 Q -15 -5 -11 -2" fill="none" stroke="#ffffff" stroke-width="1"/>"""
        elif itype == 'email':
            icon_svg = f"""<circle cx="-15" cy="-5" r="12" fill="{theme_color}"/>
      <rect x="-21" y="-10" width="12" height="9" rx="1" fill="none" stroke="#ffffff" stroke-width="1.5"/>
      <path d="M -21 -9 L -15 -5 L -9 -9" fill="none" stroke="#ffffff" stroke-width="1.5"/>"""
      
        lines.append(f"""    <g transform="translate({x}, 35)">
      {icon_svg}
      <text x="5" y="0" fill="#ffffff" font-family="system-ui, sans-serif" font-size="14" font-weight="700">{val}</text>
    </g>""")
    return f"""  <g transform="translate(0, 740)">
{"".join(lines)}
  </g>"""


def build_svg_from_data(data: dict, website=None) -> str:
    theme = data.get("theme", "theme1")
    title_lines = data.get("title_lines", [])
    subtext = data.get("subtext", "")
    cta_text = data.get("cta_text", "READ MORE")
    badges = data.get("badges", [])
    
    screen_data = data.get("laptop_screen", {})
    screen_title = screen_data.get("title", "DEVEX").strip()
    screen_subtitle = screen_data.get("subtitle", "Success Guide").strip()
    
    # Escape screen titles for SVG
    screen_title_esc = screen_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    screen_subtitle_esc = screen_subtitle.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Check for custom logo and contact details
    from django.conf import settings
    import os
    import base64
    import requests
    from urllib.parse import urlparse

    phone = "+91 9875905952"
    domain = "www.devexhub.in"
    email = "info@devexhub.com"
    logo_url = ""
    
    if website:
        phone = website.contact_phone
        if website.domain:
            domain = website.domain
        elif website.url:
            domain = urlparse(website.url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
        email = website.contact_email or f"info@{domain}"
        logo_url = website.logo_url

    custom_logo_data_uri = None
    try:
        if logo_url:
            if logo_url.startswith('/static/'):
                rel_path = logo_url.replace('/static/', '')
                logo_path = os.path.join(settings.BASE_DIR, 'frontend', rel_path)
                if os.path.exists(logo_path):
                    ext = logo_path.split('.')[-1].lower()
                    with open(logo_path, 'rb') as f:
                        encoded = base64.b64encode(f.read()).decode('utf-8')
                    mime = f"image/{ext}" if ext != 'svg' else "image/svg+xml"
                    custom_logo_data_uri = f"data:{mime};base64,{encoded}"
            elif logo_url.startswith('http://') or logo_url.startswith('https://'):
                resp = requests.get(logo_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                if resp.status_code == 200:
                    ext = logo_url.split('.')[-1].lower()
                    if ext not in ['svg', 'png', 'jpg', 'jpeg', 'gif']:
                        ext = 'png'
                    mime = f"image/{ext}" if ext != 'svg' else "image/svg+xml"
                    encoded = base64.b64encode(resp.content).decode('utf-8')
                    custom_logo_data_uri = f"data:{mime};base64,{encoded}"
    except Exception as logo_err:
        logger.warning(f"Failed to load logo_url: {logo_err}")
        
    if not custom_logo_data_uri:
        media_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media')
        try:
            for ext in ['svg', 'png', 'jpg', 'jpeg']:
                logo_path = os.path.join(media_dir, f'devexhub_logo.{ext}')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        encoded = base64.b64encode(f.read()).decode('utf-8')
                    mime = f"image/{ext}" if ext != 'svg' else "image/svg+xml"
                    custom_logo_data_uri = f"data:{mime};base64,{encoded}"
                    break
        except Exception:
            pass
        
    if custom_logo_data_uri:
        if theme == "theme3":
            logo_content_svg = f'<image href="{custom_logo_data_uri}" x="0" y="0" width="100" height="100"/>'
        else:
            logo_content_svg = f"""<rect x="-10" y="-10" width="120" height="120" rx="12" fill="#ffffff" filter="url(#shadow)"/>
    <image href="{custom_logo_data_uri}" x="0" y="0" width="100" height="100"/>"""
    else:
        logo_content_svg = """<rect x="0" y="0" width="56" height="56" rx="10" fill="none" stroke="currentColor" stroke-width="3"/>
    <polygon points="28,8 42,15 28,22 14,15" fill="currentColor"/>
    <path d="M 21 16 L 21 21 Q 28 25 35 21 L 35 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
    <path d="M 42 15 L 44 22 L 44 26" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <rect x="21" y="26" width="5" height="18" rx="1.5" fill="currentColor"/>
    <rect x="30" y="26" width="5" height="18" rx="1.5" fill="currentColor"/>
    <rect x="25" y="32" width="6" height="4" fill="currentColor"/>"""

    # 1. Render title lines
    title_lines_svg = []
    y_offset = 0
    for line in title_lines:
        text = line.get("text", "").strip()
        ltype = line.get("type", "plain")
        text_escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        if not text_escaped:
            continue
            
        if ltype == "boxed":
            box_width = len(text) * 22 + 20
            if box_width < 120:
                box_width = 120
            if theme == "theme3":
                title_lines_svg.append(f'<rect x="-10" y="{y_offset - 38}" width="{box_width}" height="50" rx="6" fill="none" stroke="#0a122c" stroke-width="2.5"/>')
                title_lines_svg.append(f'<text x="0" y="{y_offset}" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="36" fill="#0a122c">{text_escaped}</text>')
            else:
                title_lines_svg.append(f'<rect x="-10" y="{y_offset - 38}" width="{box_width}" height="50" rx="6" fill="none" stroke="#ffffff" stroke-width="2.5"/>')
                title_lines_svg.append(f'<text x="0" y="{y_offset}" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="36" fill="#ffffff">{text_escaped}</text>')
        elif ltype == "accent":
            if theme == "theme2":
                title_lines_svg.append(f'<text x="0" y="{y_offset}" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="36" fill="#22d3ee">{text_escaped}</text>')
            elif theme == "theme3":
                title_lines_svg.append(f'<text x="0" y="{y_offset}" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="36" fill="#0284c7">{text_escaped}</text>')
            else:
                title_lines_svg.append(f'<text x="0" y="{y_offset}" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="36" fill="#38bdf8">{text_escaped}</text>')
        else:
            if theme == "theme3":
                title_lines_svg.append(f'<text x="0" y="{y_offset}" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="36" fill="#0a122c">{text_escaped}</text>')
            else:
                title_lines_svg.append(f'<text x="0" y="{y_offset}" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="36" fill="#ffffff">{text_escaped}</text>')
        y_offset += 54
        
    title_lines_svg_str = "\n    ".join(title_lines_svg)

    # 2. Render subtext lines
    subtext_lines = wrap_text(subtext, 42)
    subtext_svg_lines = []
    dy = 0
    for sline in subtext_lines:
        sline_escaped = sline.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        subtext_svg_lines.append(f'<tspan x="80" dy="{dy}">{sline_escaped}</tspan>')
        dy = 24
    subtext_svg_str = "\n    ".join(subtext_svg_lines)

    # 3. Render badges and connections
    badge_positions = [
        (650, 140),
        (840, 100),
        (1010, 150),
        (1030, 450)
    ]
    badges_svg_lines = []
    connections_svg_lines = []
    
    if theme == "theme2":
        stroke_color = "#d946ef"
        theme_color = "#7c3aed"
    elif theme == "theme3":
        stroke_color = "#cbd5e1"
        theme_color = "#0284c7"
    else:
        stroke_color = "#94a3b8"
        theme_color = "#0284c7"
        
    footer_svg = build_footer_svg(phone, domain, email, theme_color)
        
    # Standard connection lines (dotted)
    connections_svg_lines.append(f'<path d="M 720 182 Q 720 280 810 280" fill="none" stroke="{stroke_color}" stroke-width="2" stroke-dasharray="4,4"/>')
    connections_svg_lines.append(f'<path d="M 890 142 Q 890 260 840 260" fill="none" stroke="{stroke_color}" stroke-width="2" stroke-dasharray="4,4"/>')
    connections_svg_lines.append(f'<path d="M 1010 192 Q 970 260 870 260" fill="none" stroke="{stroke_color}" stroke-width="2" stroke-dasharray="4,4"/>')
    connections_svg_lines.append(f'<path d="M 1030 470 Q 950 470 900 420" fill="none" stroke="{stroke_color}" stroke-width="2" stroke-dasharray="4,4"/>')
    
    for i, badge in enumerate(badges[:4]):
        label = badge.get("label", "Tech").strip()
        color = badge.get("color", "#3b82f6").strip()
        bx, by = badge_positions[i]
        label_escaped = label.replace("&", "&amp;").replace("<", "&lt;").replace(">/", "&gt;")
        bw = len(label) * 9 + 50
        if bw < 100:
            bw = 100
            
        if theme == "theme2":
            badges_svg_lines.append(f"""
    <g transform="translate({bx}, {by})" filter="url(#shadow)">
      <rect x="0" y="0" width="{bw}" height="42" rx="10" fill="#111827" stroke="{color}" stroke-width="2"/>
      <circle cx="20" cy="21" r="6" fill="{color}"/>
      <text x="36" y="26" font-family="system-ui, sans-serif" font-size="14" font-weight="700" fill="#f3f4f6">{label_escaped}</text>
    </g>""")
        elif theme == "theme3":
            badges_svg_lines.append(f"""
    <g transform="translate({bx}, {by})" filter="url(#shadow)">
      <rect x="0" y="0" width="{bw}" height="42" rx="10" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5"/>
      <circle cx="20" cy="21" r="6" fill="{color}"/>
      <text x="36" y="26" font-family="system-ui, sans-serif" font-size="14" font-weight="700" fill="#0f172a">{label_escaped}</text>
    </g>""")
        else:
            badges_svg_lines.append(f"""
    <g transform="translate({bx}, {by})" filter="url(#shadow)">
      <rect x="0" y="0" width="{bw}" height="42" rx="10" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.5"/>
      <circle cx="20" cy="21" r="6" fill="{color}"/>
      <text x="36" y="26" font-family="system-ui, sans-serif" font-size="14" font-weight="700" fill="#1e293b">{label_escaped}</text>
    </g>""")
            
    badges_svg_str = "\n".join(badges_svg_lines)
    connections_svg_str = "\n".join(connections_svg_lines)
    
    # 4. Templates
    if theme == "theme2":
        svg = f"""<svg width="1200" height="800" viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000000" flood-opacity="0.3"/>
    </filter>
    <linearGradient id="purpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7c3aed"/>
      <stop offset="100%" stop-color="#db2777"/>
    </linearGradient>
    <pattern id="cyberGrid" width="50" height="50" patternUnits="userSpaceOnUse">
      <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#111827" stroke-width="1"/>
    </pattern>
  </defs>

  <rect x="0" y="0" width="1200" height="800" fill="#090d16"/>
  <rect x="0" y="0" width="1200" height="740" fill="url(#cyberGrid)"/>

  <path d="M 0 0 L 540 0 Q 590 370 470 740 L 0 740 Z" fill="#0f172a" opacity="0.95"/>
  <path d="M 0 0 L 540 0 Q 590 370 470 740 L 0 740 Z" fill="none" stroke="url(#purpleGrad)" stroke-width="3"/>

  <g transform="translate(80, 50)" color="#ffffff">
    {logo_content_svg}
  </g>

  <g id="title-text" transform="translate(80, 200)">
     {title_lines_svg_str}
  </g>

  <text x="80" y="470" font-family="system-ui, sans-serif" font-size="16" font-weight="500" fill="#cbd5e1" opacity="0.9">
     {subtext_svg_str}
  </text>

  <g transform="translate(80, 560)">
    <rect x="0" y="0" width="180" height="48" rx="24" fill="url(#purpleGrad)" filter="url(#shadow)"/>
    <text x="90" y="29" font-family="system-ui, sans-serif" font-size="14" font-weight="800" fill="#ffffff" text-anchor="middle" letter-spacing="1">{cta_text}</text>
    <path d="M 145 20 L 151 24 L 145 28 M 138 24 L 150 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  {connections_svg_str}

  <circle cx="850" cy="380" r="140" fill="#7c3aed" opacity="0.08" filter="blur(30px)"/>

  <g id="laptop" transform="translate(60, 20)">
    <rect x="660" y="230" width="360" height="230" rx="12" fill="#030712" stroke="#4b5563" stroke-width="4"/>
    <rect x="670" y="240" width="340" height="210" rx="4" fill="#090d16"/>
    <g transform="translate(840, 345)">
      <circle cx="-40" cy="-30" r="8" fill="#a855f7"/>
      <circle cx="40" cy="-30" r="8" fill="#ec4899"/>
      <circle cx="-60" cy="20" r="8" fill="#3b82f6"/>
      <circle cx="60" cy="20" r="8" fill="#14b8a6"/>
      <circle cx="0" cy="40" r="10" fill="#22d3ee"/>
      <line x1="-40" y1="-30" x2="0" y2="40" stroke="#4b5563" stroke-width="2"/>
      <line x1="40" y1="-30" x2="0" y2="40" stroke="#4b5563" stroke-width="2"/>
      <line x1="-60" y1="20" x2="0" y2="40" stroke="#4b5563" stroke-width="2"/>
      <line x1="60" y1="20" x2="0" y2="40" stroke="#4b5563" stroke-width="2"/>
      <line x1="-40" y1="-30" x2="40" y2="-30" stroke="#4b5563" stroke-width="1.5" stroke-dasharray="2,2"/>
    </g>
    <text x="840" y="420" font-family="system-ui, sans-serif" font-size="28" font-weight="900" fill="#22d3ee" text-anchor="middle" letter-spacing="3">{screen_title_esc}</text>
    
    <polygon points="610,460 1070,460 1030,485 650,485" fill="#1f2937"/>
    <polygon points="650,485 1030,485 1020,492 660,492" fill="#111827"/>
    <rect x="800" y="465" width="80" height="14" rx="2" fill="#111827"/>
  </g>

  {badges_svg_str}

  <rect x="0" y="740" width="1200" height="60" fill="#030712"/>
  {footer_svg}
</svg>"""

    elif theme == "theme3":
        svg = f"""<svg width="1200" height="800" viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#0f172a" flood-opacity="0.12"/>
    </filter>
    <linearGradient id="darkBlueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a192f"/>
      <stop offset="100%" stop-color="#172a45"/>
    </linearGradient>
  </defs>

  <rect x="0" y="0" width="1200" height="800" fill="#ffffff"/>

  <path d="M 720 0 Q 640 370 760 740 L 1200 740 L 1200 0 Z" fill="url(#darkBlueGrad)"/>

  <g transform="translate(80, 50)" color="#0a122c">
    {logo_content_svg}
  </g>

  <g id="title-text" transform="translate(80, 200)">
     {title_lines_svg_str}
  </g>

  <text x="80" y="470" font-family="system-ui, sans-serif" font-size="16" font-weight="500" fill="#475569" opacity="0.95">
     {subtext_svg_str}
  </text>

  <g transform="translate(80, 560)">
    <rect x="0" y="0" width="180" height="48" rx="24" fill="#0a122c" filter="url(#shadow)"/>
    <text x="90" y="29" font-family="system-ui, sans-serif" font-size="14" font-weight="800" fill="#ffffff" text-anchor="middle" letter-spacing="1">{cta_text}</text>
    <path d="M 145 20 L 151 24 L 145 28 M 138 24 L 150 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  {connections_svg_str}

  <g id="laptop" transform="translate(80, 20)">
    <rect x="660" y="230" width="360" height="230" rx="12" fill="#0f172a" stroke="#4b5563" stroke-width="4"/>
    <rect x="670" y="240" width="340" height="210" rx="4" fill="#020617"/>
    <g transform="translate(685, 255)" fill="#60a5fa" font-family="Courier, monospace" font-size="11">
      <text x="0" y="0">
        <tspan x="0" dy="16" fill="#f43f5e">&lt;?php</tspan>
        <tspan x="0" dy="16" fill="#e2e8f0">class WebApp {{</tspan>
        <tspan x="0" dy="16" fill="#e2e8f0">  public function render() {{</tspan>
        <tspan x="4" dy="16" fill="#a855f7">    $theme = "DevexHub";</tspan>
        <tspan x="4" dy="16" fill="#34d399">    return view($theme);</tspan>
        <tspan x="0" dy="16" fill="#e2e8f0">  }}</tspan>
        <tspan x="0" dy="16" fill="#e2e8f0">}}</tspan>
      </text>
    </g>
    <rect x="850" y="405" width="140" height="34" rx="6" fill="#1e293b" opacity="0.9"/>
    <text x="920" y="427" font-family="system-ui, sans-serif" font-size="13" font-weight="800" fill="#ffffff" text-anchor="middle">{screen_subtitle_esc}</text>
    
    <polygon points="610,460 1070,460 1030,485 650,485" fill="#475569"/>
    <polygon points="650,485 1030,485 1020,492 660,492" fill="#334155"/>
    <rect x="800" y="465" width="80" height="14" rx="2" fill="#334155"/>
  </g>

  {badges_svg_str}

  <rect x="0" y="740" width="1200" height="60" fill="#0a122c"/>
  {footer_svg}
</svg>"""

    else:
        svg = f"""<svg width="1200" height="800" viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#0f172a" flood-opacity="0.15"/>
    </filter>
    <linearGradient id="blueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284c7"/>
      <stop offset="100%" stop-color="#1e3a8a"/>
    </linearGradient>
    <pattern id="hexGrid" width="40" height="69.282" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 20 11.547 L 0 0 L 0 23.094 L 20 34.641 L 40 23.094 Z M 0 34.641 L 20 46.188 L 0 57.735 L 0 80.829 L 20 92.376 L 40 80.829 L 40 57.735 L 20 46.188" fill="none" stroke="#cbd5e1" stroke-width="0.8"/>
    </pattern>
  </defs>

  <rect x="0" y="0" width="1200" height="800" fill="#f8fafc"/>
  <rect x="450" y="0" width="750" height="740" fill="url(#hexGrid)" opacity="0.3"/>

  <path d="M 0 0 L 520 0 Q 570 370 460 740 L 0 740 Z" fill="url(#blueGrad)"/>

  <g transform="translate(80, 50)" color="#ffffff">
    {logo_content_svg}
  </g>

  <g id="title-text" transform="translate(80, 200)">
     {title_lines_svg_str}
  </g>

  <text x="80" y="470" font-family="system-ui, sans-serif" font-size="16" font-weight="500" fill="#e2e8f0" opacity="0.95">
     {subtext_svg_str}
  </text>

  <g transform="translate(80, 560)">
    <rect x="0" y="0" width="180" height="48" rx="24" fill="#0284c7" filter="url(#shadow)"/>
    <text x="90" y="29" font-family="system-ui, sans-serif" font-size="14" font-weight="800" fill="#ffffff" text-anchor="middle" letter-spacing="1">{cta_text}</text>
    <path d="M 145 20 L 151 24 L 145 28 M 138 24 L 150 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  {connections_svg_str}
  
  <g id="laptop" transform="translate(50, 0)">
    <rect x="660" y="250" width="360" height="230" rx="12" fill="#0f172a" stroke="#334155" stroke-width="4"/>
    <rect x="670" y="260" width="340" height="210" rx="4" fill="#1e293b"/>
    <text x="840" y="360" font-family="system-ui, sans-serif" font-size="52" font-weight="900" fill="#ffffff" text-anchor="middle" letter-spacing="2">{screen_title_esc}</text>
    <circle cx="910" cy="370" r="14" fill="none" stroke="#0284c7" stroke-width="4"/>
    <line x1="920" y1="380" x2="935" y2="395" stroke="#0284c7" stroke-width="4" stroke-linecap="round"/>
    
    <polygon points="610,480 1070,480 1030,505 650,505" fill="#475569"/>
    <polygon points="650,505 1030,505 1020,512 660,512" fill="#334155"/>
    <rect x="800" y="485" width="80" height="16" rx="3" fill="#334155"/>
  </g>

  <g transform="translate(640, 480)">
    <polygon points="-10,-10 10,-10 7,15 -7,15" fill="#f43f5e"/>
    <path d="M 0 -10 Q -15 -25 -20 -30 Q -7 -22 0 -10 Z" fill="#10b981"/>
    <path d="M 0 -10 Q 15 -25 20 -30 Q 7 -22 0 -10 Z" fill="#10b981"/>
    <path d="M 0 -10 Q 0 -35 0 -40 Q 5 -25 0 -10 Z" fill="#10b981"/>
  </g>
  
  <g transform="translate(970, 485) rotate(15)">
    <rect x="0" y="0" width="70" height="50" rx="4" fill="#ffffff" stroke="#cbd5e1" stroke-width="2"/>
    <path d="M -5 10 L 2 8 M -3 20 L 4 18 M -1 30 L 6 28" stroke="#94a3b8" stroke-width="2.5"/>
    <rect x="80" y="-10" width="5" height="55" rx="1.5" fill="#0f172a" transform="rotate(-45 80 -10)"/>
  </g>

  {badges_svg_str}

  <rect x="0" y="740" width="1200" height="60" fill="#0a122c"/>
  {footer_svg}
</svg>"""

    return svg


def generate_svg_cover_via_gpt(title: str, category: str, excerpt: str = "", website=None) -> str:
    """Uses GPT-4o-mini to plan a stylized blog cover, then renders it using a local template."""
    prompt = f"""You are an expert graphic designer. You are designing a blog cover layout for:
BLOG TITLE: {title}
BLOG CATEGORY: {category}
BLOG EXCERPT/SUMMARY: {excerpt}

Based on this category, title, and excerpt summary, you must plan the cover illustration. We support three visual themes:
- "theme1" (SEO / Digital Marketing / Business / Growth): Light right side, blue/indigo curved gradient sidebar on the left.
- "theme2" (Artificial Intelligence / Technology / Machine Learning): Dark high-tech theme with a neon purple-to-pink glowing curved sidebar.
- "theme3" (Web Development / Coding / Full Stack / PHP / software engineering): White background on the left, dark blue/indigo curved sidebar on the right.

Your task is to analyze the title, category, and excerpt to select the best theme and provide structured details for rendering that are highly relevant to the actual blog content.

Return a JSON object with the following keys:
1. "theme": Select "theme1", "theme2", or "theme3".
   - Select "theme2" for AI, machine learning, agents, or deep learning.
   - Select "theme3" for coding, web development, PHP, full stack, database, or engineering.
   - Select "theme1" for SEO, marketing, business, growth, or any general topics.
2. "title_lines": Break the title into 2-4 short lines (each line under 28 characters) so it fits inside the left column beautifully.
   Each line in "title_lines" is an object:
   {{
     "text": "The line text",
     "type": "plain" | "boxed" | "accent"
   }}
   - "boxed": wraps the text in a styled rectangle border (use for key keywords, max 1 boxed line per title).
   - "accent": uses the secondary highlight color (light blue or purple).
   - "plain": uses the standard text color (white or dark blue depending on the theme).
3. "subtext": A concise 1-2 sentence description summarizing the value of the post (max 120 characters total).
4. "cta_text": The button text, e.g. "READ MORE", "LEARN MORE", "EXPLORE NOW".
5. "laptop_screen": An object representing what is shown on the laptop:
   - "title": A short bold title (1-2 words, e.g., "SEO", "AI", "CODE", "PHP", "ML") to display.
   - "subtitle": A tiny subtitle (2-3 words, e.g. "Search Analytics", "Neural Network", "Full Stack").
6. "badges": A list of exactly 4 floating badge cards. Each badge represents a relevant tool, technology, or concept:
   - For example:
     - For Web Dev: "HTML/CSS", "JavaScript", "PHP", "React", "NodeJS", "MySQL", "GitHub".
     - For AI: "ChatGPT", "Gemini", "Perplexity", "Claude", "LLMs", "Agents", "NLP".
     - For SEO: "Google", "Rankings", "Keywords", "Analytics", "Audits", "Content".
   Each badge is an object:
   {{
     "label": "Badge label (max 12 chars)",
     "color": "A hex color code for the badge icon (e.g. #3b82f6, #ec4899, #10b981)"
   }}

Do NOT include any markdown formatting. Return ONLY the raw JSON object."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=800,
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        
        import json
        data = json.loads(response.choices[0].message.content.strip())
        svg_content = build_svg_from_data(data, website=website)
        if svg_content:
            return svg_content
    except Exception as e:
        logger.warning(f"GPT SVG cover planning failed: {e}. Falling back to local heuristic.")
        
    # Heuristic Fallback
    try:
        import json
        theme = "theme1"
        cat_lower = category.lower() if category else ""
        title_lower = title.lower() if title else ""
        if any(k in cat_lower or k in title_lower for k in ["ai", "agent", "machine learning", "intelligence", "neural", "gpt"]):
            theme = "theme2"
        elif any(k in cat_lower or k in title_lower for k in ["web", "develop", "php", "code", "programming", "sql", "html", "css", "js", "javascript", "stack"]):
            theme = "theme3"
            
        words = title.split()
        lines = []
        curr = []
        curr_len = 0
        for w in words:
            if curr_len + len(w) + 1 > 24:
                lines.append(" ".join(curr))
                curr = [w]
                curr_len = len(w)
            else:
                curr.append(w)
                curr_len += len(w) + 1
        if curr:
            lines.append(" ".join(curr))
            
        title_lines = []
        for i, line in enumerate(lines[:4]):
            ltype = "boxed" if i == 1 else ("accent" if i == 3 else "plain")
            title_lines.append({"text": line, "type": ltype})
            
        fallback_data = {
            "theme": theme,
            "title_lines": title_lines,
            "subtext": f"A detailed guide to {title}.",
            "cta_text": "READ MORE",
            "laptop_screen": {
                "title": "DEVEX",
                "subtitle": "Knowledge Base"
            },
            "badges": [
                {"label": "Devex Hub", "color": "#0ea5e9"},
                {"label": "Success", "color": "#10b981"},
                {"label": "Learning", "color": "#f59e0b"},
                {"label": "Growth", "color": "#8b5cf6"}
            ]
        }
        return build_svg_from_data(fallback_data, website=website)
    except Exception as fallback_err:
        logger.error(f"Fallback SVG generation also failed: {fallback_err}")
    return ""


def generate_for_idea(idea_id: int):
    """Main entry point called by Celery task."""
    from .models import ContentIdea, ContentDraft
    
    idea = ContentIdea.objects.select_related('website').get(pk=idea_id)
    website = idea.website
    
    try:
        cover_image_url = ""
        category_name = ""
        if idea.platform == 'blog':
            content_data = generate_blog_post(idea, website)
            category_name = content_data.get('category', 'General')
            
            # Generate cover image using GPT (SVG vector art)
            try:
                from django.conf import settings
                import os
                import uuid
                
                logger.info(f"Generating GPT SVG cover image for blog: {idea.title}")
                svg_code = generate_svg_cover_via_gpt(
                    idea.title, 
                    category_name, 
                    excerpt=content_data.get('excerpt', ''), 
                    website=website
                )
                
                if svg_code:
                    media_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media')
                    os.makedirs(media_dir, exist_ok=True)
                    
                    filename = f"blog_cover_{uuid.uuid4().hex}.svg"
                    filepath = os.path.join(media_dir, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(svg_code)
                        
                    cover_image_url = f"/static/media/{filename}"
                    logger.info(f"Successfully generated and saved GPT SVG cover image to: {cover_image_url}")
            except Exception as img_err:
                logger.warning(f"Failed to generate GPT SVG cover image: {img_err}")
        else:
            content_data = generate_social_post(idea, website, idea.platform)
        
        draft = ContentDraft.objects.create(
            idea=idea,
            website=website,
            platform=idea.platform,
            title=content_data.get('title', idea.title),
            body=content_data.get('body', ''),
            excerpt=content_data.get('excerpt', ''),
            meta_description=content_data.get('meta_description', ''),
            tags=content_data.get('tags', []),
            ai_model=content_data.get('ai_model', MODEL),
            generation_prompt=content_data.get('generation_prompt', ''),
            status='draft',
            cover_image=cover_image_url,
            category=category_name,
        )
        
        idea.status = 'done'
        idea.save(update_fields=['status'])
        
        return draft.id
    
    except Exception as e:
        logger.warning(f"AI generation failed, falling back to local simulation: {e}")
        try:
            if idea.platform == 'blog':
                fallback_data = get_rich_fallback_blog(idea.title)
                body = fallback_data['body']
                excerpt = fallback_data['excerpt']
                tags = fallback_data['tags']
                meta_desc = fallback_data['meta_description']
                category_name = fallback_data['category']
                title_val = fallback_data['title']
            else:
                body = f"🚀 Exploring {idea.title}! Consistent content is key to building a strong digital presence. What are your thoughts on this? 👇 #cadence #contentmarketing #ai"
                excerpt = body
                tags = ["content", "ai"]
                meta_desc = ""
                category_name = ""
                title_val = idea.title

            draft = ContentDraft.objects.create(
                idea=idea,
                website=website,
                platform=idea.platform,
                title=title_val,
                body=body,
                excerpt=excerpt,
                meta_description=meta_desc,
                tags=tags,
                ai_model='local-fallback',
                generation_prompt='Simulated Prompt (OpenAI Fallback)',
                status='draft',
                cover_image="",
                category=category_name,
            )
            idea.status = 'done'
            idea.save(update_fields=['status'])
            return draft.id
        except Exception as inner_e:
            idea.status = 'failed'
            idea.save(update_fields=['status'])
            logger.error(f"Fallback generation also failed: {inner_e}")
            raise e


def analyze_website_context(structure_text: str) -> dict:
    """
    Uses GPT to extract structured metadata (industry, tone, topics, brand_colors, avg_read_time)
    from the crawled structure text.
    """
    prompt = f"""Analyze this website structure and content:
{structure_text[:6000]}

Extract the following details as a JSON object:
1. "industry": A single professional industry name (e.g. "Food & Beverage", "Technology", "Fitness & Health", "Travel & Tourism", "Fashion & Apparel").
2. "tone": A description of the writing tone (e.g. "Warm, artisanal", "Professional, technical", "Energetic, motivational", "Friendly, casual").
3. "topics": A list of up to 10 specific core topics discussed on the site (e.g. ["Specialty coffee", "Latte art", "Brewing guides"]).
4. "brand_colors": A list of 5 hex color codes representing the visual brand palette (suggested colors based on the website context if CSS is not present). Return EXACT hex codes (e.g. ["#b45309", "#78350f", "#f5e6d3", "#1c1917", "#d97706"]).
5. "avg_read_time": Estimate the average read time of a typical article on the site (e.g. "4.5m").

Return ONLY a valid JSON object with these keys. Do NOT include markdown code blocks."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=600,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        import json
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Failed to analyze website context with GPT: {e}")
        return {
            "industry": "General Business",
            "tone": "Professional, engaging",
            "topics": ["Company news", "Industry insights", "Product updates"],
            "brand_colors": ["#6366f1", "#4f46e5", "#f5f3ff", "#1f2937", "#a5b4fc"],
            "avg_read_time": "3.5m"
        }