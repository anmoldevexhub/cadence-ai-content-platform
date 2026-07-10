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
client = OpenAI(api_key=config('OPENAI_API_KEY'), timeout=90.0, max_retries=5)

MODEL = config('AI_MODEL', default='gpt-4o-mini')

def call_llm(prompt, system_prompt=None, max_tokens=600, temperature=0.7, json_mode=False, website=None, section='general'):
    """Routes LLM request to OpenAI or Gemini depending on the configured model."""
    model_name = config('AI_MODEL', default='gpt-4o-mini')
    
    if 'gemini' in model_name.lower():
        import requests
        import json
        
        api_key = config('GEMINI_API_KEY', default=config('GOOGLE_API_KEY', default=None))
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        
        combined_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        payload = {
            "contents": [{"parts": [{"text": combined_prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature
            }
        }
        
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
            
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        result = response.json()
        
        # log token usage
        usage = result.get('usageMetadata', {})
        prompt_tokens = usage.get('promptTokenCount', 0)
        completion_tokens = usage.get('candidatesTokenCount', 0)
        if prompt_tokens or completion_tokens:
            log_token_usage(website, section, model_name, prompt_tokens, completion_tokens)
            
        text = result['candidates'][0]['content']['parts'][0]['text']
        if json_mode:
            try:
                return json.loads(text.strip())
            except Exception:
                # try cleaning markdown code block formatting
                cleaned = text.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
                return json.loads(cleaned)
        return text
    else:
        # OpenAI
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        
        args = {
            'model': model_name,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        if json_mode:
            args['response_format'] = {"type": "json_object"}
            
        response = client.chat.completions.create(**args)
        
        if hasattr(response, 'usage') and response.usage:
            log_token_usage(website, section, model_name, response.usage.prompt_tokens, response.usage.completion_tokens)
            
        text = response.choices[0].message.content.strip()
        if json_mode:
            import json
            return json.loads(text)
        return text


def log_token_usage(website, section, model_name, prompt_tokens, completion_tokens):
    """Logs LLM token usage and calculates estimated cost."""
    try:
        from .models import TokenUsage
        cost = 0.0
        # pricing rules
        if 'gpt-4o-mini' in model_name:
            cost = (prompt_tokens * 0.00000015) + (completion_tokens * 0.00000060)
        elif 'dall-e-3' in model_name:
            cost = 0.040
        elif 'gemini' in model_name:
            cost = (prompt_tokens * 0.000000075) + (completion_tokens * 0.00000030)
        else:
            cost = (prompt_tokens + completion_tokens) * 0.0000002
            
        TokenUsage.objects.create(
            website=website,
            section=section,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost
        )
    except Exception as e:
        logger.error(f"Error logging token usage: {e}")


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
    
    try:
        return call_llm(prompt, max_tokens=600, temperature=0.3, section='crawler_summary')
    except Exception as e:
        logger.error(f"Failed to summarize website style: {e}")
        return (
            "Write in a professional, clear, and engaging tone. Structure the content logically with an introduction, "
            "subheadings, and clear call-to-actions. Keep the paragraphs concise and use bullet points for readability. "
            "Target key audience interests and write in a brand-consistent voice."
        )


def build_system_prompt(website: Website, platform: str = 'blog') -> str:
    """Builds system prompt. Uses minimal style guide if user-provided samples are active,
    or falls back to crawled style guide metrics if no samples are active for the platform."""
    has_samples = website.samples.filter(platform=platform, is_active=True).exists()
    
    blog_guidelines = ""
    if platform == 'blog':
        blog_guidelines = """When writing blog posts:
- Always write a detailed, comprehensive, deep-dive article of at least 900 to 1200 words. Do not stop until you have covered the topic in full depth.
- Avoid brief outlines or summaries. Write in simple, everyday English (no corporate jargon or complex AI words like "leverage", "optimize", "streamline", "redouble", "game changer", "testament", or "delve").
- Vary sentence lengths dramatically. Use very short, punchy sentences alongside longer, conversational ones.
- Avoid perfectly symmetrical section structures. Make layout, section length, and bullet points uneven and varied.
- Never write textbook-like or encyclopedia-style explanations. Talk like a real, experienced practitioner.
- Never break character or mention that you are an AI."""
    
    if has_samples:
        prompt_str = f"""You are an expert content writer for {website.name} ({website.domain}).

BRAND: {website.name}
INDUSTRY: {website.industry or "General"}
KEY TOPICS: {", ".join(website.topics) if website.topics else "General content"}

Write in the same style as the samples provided in the user prompt."""
        if blog_guidelines:
            prompt_str += f"\n\n{blog_guidelines}"
        return prompt_str

    # Fallback to crawler/style guide
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

{blog_guidelines if blog_guidelines else "Write in a natural, engaging tone."}"""


def get_style_reference(website: Website, platform: str) -> str:
    """Fetch 5-7 user-uploaded samples for a specific platform, or fall back to crawled data."""
    from websites.models import SampleContent, ScrapeResult
    
    samples = SampleContent.objects.filter(
        website=website,
        platform=platform,
        is_active=True
    ).order_by('-uploaded_at')[:7]
    
    if samples:
        style_text = ""
        for i, sample in enumerate(samples, 1):
            content = sample.content[:3000] if len(sample.content) > 3000 else sample.content
            style_text += f"""
================================================================================
SAMPLE {i} ({platform.upper()}):
================================================================================
{'TITLE: ' + sample.title if sample.title else ''}
CONTENT:
{content}
================================================================================
"""
        return style_text
        
    # Fallback to ScrapeResult (crawled data)
    scrapes = ScrapeResult.objects.filter(website=website)[:5]
    if not scrapes:
        try:
            from websites.tasks import crawl_website_task
            logger.info(f"No samples or crawled content found for website {website.name}. Running crawl synchronously...")
            crawl_website_task(website.id)
            # Re-fetch scrapes
            scrapes = ScrapeResult.objects.filter(website=website)[:5]
        except Exception as e:
            logger.error(f"Failed to crawl website {website.id} on-the-fly: {e}")

    if scrapes:
        style_text = "CRAWLED SAMPLES (Fallback):\n"
        for i, scrape in enumerate(scrapes, 1):
            content = scrape.main_content or scrape.raw_text
            content = content[:2000] if len(content) > 2000 else content
            style_text += f"""
================================================================================
CRAWLED SAMPLE {i}:
================================================================================
TITLE: {scrape.page_title}
URL: {scrape.page_url}
CONTENT:
{content}
================================================================================
"""
        return style_text
        
    return "No samples or crawled content available. Please upload sample content or crawl the website first."


def get_style_reference_samples(website: Website, platform: str) -> str:
    """Legacy wrapper for get_style_reference to maintain test compatibility."""
    return get_style_reference(website, platform)


def generate_idea_suggestions(website: Website) -> list:
    """
    Generates 8 dynamic AI-powered content idea suggestions for a website.
    Uses the website's industry, topics, and scrape_summary plus a live trend
    search via DuckDuckGo to suggest relevant, timely content.
    Returns a list of dicts: [{"title": str, "platform": str, "reason": str}]
    """
    import json as _json
    from datetime import date

    # Build context about the website
    topics_str = ", ".join(website.topics[:10]) if website.topics else "general content"
    industry = website.industry or "General"
    brand_name = website.name
    style_summary = (website.scrape_summary or "")[:500]
    today = date.today().strftime("%B %Y")

    # Do a quick live trend search for the industry — skip if unavailable
    raw_trends = search_live_data(f"{industry} content marketing trends {today}")
    live_trends_section = ""
    if raw_trends and raw_trends != "No live data available.":
        live_trends_section = f"\nLIVE TRENDS CONTEXT (use to make ideas timely):\n{raw_trends}\n"

    prompt = f"""You are an expert content strategist. Generate exactly 8 content idea suggestions for the brand below.
Return your response as a JSON object with a single key "suggestions" containing an array of 8 items.

BRAND: {brand_name}
INDUSTRY: {industry}
KEY TOPICS: {topics_str}
BRAND STYLE: {style_summary if style_summary else 'Professional and informative'}
DATE: {today}
{live_trends_section}
Rules:
- Platform mix: 3 blog, 2 linkedin, 2 instagram, 1 youtube
- Titles must be specific, compelling, and relevant to the brand's industry
- Blog titles: SEO-friendly, informative
- LinkedIn titles: punchy, professional insight angle
- Instagram titles: short, visual hook
- YouTube titles: descriptive, search-optimised
- reason: one sentence explaining why this topic matters right now

Required JSON format:
{{
  "suggestions": [
    {{"title": "...", "platform": "blog", "reason": "..."}},
    {{"title": "...", "platform": "linkedin", "reason": "..."}},
    {{"title": "...", "platform": "instagram", "reason": "..."}},
    {{"title": "...", "platform": "blog", "reason": "..."}},
    {{"title": "...", "platform": "youtube", "reason": "..."}},
    {{"title": "...", "platform": "linkedin", "reason": "..."}},
    {{"title": "...", "platform": "instagram", "reason": "..."}},
    {{"title": "...", "platform": "blog", "reason": "..."}}
  ]
}}"""

    def _fallback():
        platforms = ["blog", "linkedin", "instagram", "blog", "youtube", "linkedin", "instagram", "blog"]
        first_topic = topics_str.split(',')[0].strip() if topics_str and topics_str != "general content" else industry
        titles = [
            f"Top {industry} Trends to Watch in {today}",
            f"How {brand_name} Is Shaping the Future of {industry}",
            f"Behind the Scenes at {brand_name} ✨",
            f"The Complete Guide to {first_topic}",
            f"{industry} Explained: What Every Business Needs to Know in {today}",
            f"5 Lessons from {industry} That Changed How We Work",
            f"Quick Tips for {first_topic} That Actually Work 💡",
            f"Why {industry} Leaders Are Betting on {brand_name}",
        ]
        return [
            {"title": title, "platform": platform, "reason": f"Relevant to {industry} industry trends"}
            for title, platform in zip(titles, platforms)
        ]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        parsed = _json.loads(raw)

        # Extract suggestions list from object
        suggestions = []
        if isinstance(parsed, dict):
            for val in parsed.values():
                if isinstance(val, list) and len(val) > 0:
                    suggestions = val
                    break

        # Validate and normalise
        valid_platforms = {"blog", "linkedin", "instagram", "youtube"}
        cleaned = []
        for item in suggestions[:8]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            import re
            title = re.sub(r'^\d+\s*\.\s*', '', title).strip()
            plat = str(item.get("platform", "blog")).lower()
            if plat not in valid_platforms:
                plat = "blog"
            cleaned.append({
                "title": title[:280],
                "platform": plat,
                "reason": str(item.get("reason", ""))[:200],
            })

        # If AI returned nothing useful, use fallback
        if not cleaned:
            logger.warning(f"generate_idea_suggestions got empty result for {website.domain}, using fallback")
            return _fallback()

        return cleaned

    except Exception as exc:
        logger.warning(f"generate_idea_suggestions failed for {website.domain}: {exc}")
        return _fallback()


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
        resp = requests.get(url, headers=headers, timeout=5.0)
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
        
    elif "transport" in t_lower or "traffic" in t_lower or "mobility" in t_lower or "logistics" in t_lower:
        body = """<h2>AI's Role in Revolutionizing Transportation</h2>
<p>Imagine a world where traffic jams are a thing of the past, and your daily commute is as smooth as silk. With the rise of artificial intelligence (AI) in transportation, this vision is becoming a reality. AI is not just a tool; it's a game changer that transforms how we manage traffic, logistics, and smart mobility.</p>

<p>AI enhances traffic management by leveraging real-time data analytics, enabling cities to respond dynamically to changing conditions. Traditional traffic management systems often rely on historical data and fixed signals, leading to congestion and inefficiencies. In contrast, AI can analyze data from various sources, such as traffic cameras, sensors, and GPS systems, to optimize traffic flow in real-time. This adaptability not only reduces travel times but also minimizes fuel consumption and emissions.</p>

<p>Moreover, the logistics industry is experiencing a seismic shift thanks to AI integration. Companies are harnessing machine learning algorithms to predict demand, optimize routes, and manage inventory more effectively. According to a report by McKinsey, logistics companies that adopt AI can reduce operational costs by up to 20%. This significant reduction is crucial for businesses striving to maintain competitiveness in an increasingly digital marketplace.</p>

<h2>The Impact of AI on Smart Mobility</h2>
<p>Smart mobility solutions powered by AI are redefining urban transport. From ridesharing apps to autonomous vehicles, the integration of AI enhances convenience and safety for users. For instance, AI algorithms can optimize ridesharing routes, ensuring that passengers are picked up and dropped off in the most efficient manner. This not only saves time but also reduces emissions by decreasing the number of vehicles on the road.</p>

<p>Public transportation systems are also benefiting from AI technologies. By analyzing patterns in ridership data, transit authorities can adjust service frequency and routes to meet demand more effectively. This strategic integration of AI leads to higher user satisfaction and increased ridership. In fact, cities that implement AI-driven public transport solutions have reported ridership increases of up to 30%.</p>

<h2>Real-World Applications of AI in Transportation</h2>
<p>Numerous cities worldwide are already reaping the benefits of AI in their transportation systems. For example, Los Angeles has implemented an AI-driven traffic signal optimization system that adjusts signal timing based on real-time traffic conditions. As a result, the city has reported a 20% reduction in travel times during peak hours.</p>

<p>Furthermore, logistics giants like Amazon are leveraging AI to streamline their supply chains. By using predictive analytics, they can anticipate product demand and adjust inventory levels accordingly. This proactive approach helps reduce waste and improve customer satisfaction, demonstrating the transformative power of AI.</p>

<h2>The Challenges Ahead</h2>
<p>Despite the promising advancements, the integration of AI in transportation is not without its challenges. Concerns around data privacy, security, and the potential for job loss in traditional roles must be addressed. As cities and companies move toward AI-driven solutions, it's crucial to implement robust regulatory frameworks to protect users and ensure ethical practices.</p>

<p>Moreover, the initial investment required for AI technologies can be significant, deterring some organizations from making the leap. However, the long-term savings and efficiency gains often outweigh the upfront costs, making a compelling case for adoption.</p>

<h2>Preparing for the Future of Transportation</h2>
<p>As AI continues to evolve, the transportation landscape will inevitably shift. Cities and organizations must prepare for this change by investing in AI solutions and fostering a culture of innovation. Collaboration between public and private sectors will be essential to develop integrated systems that enhance the overall transportation experience.</p>

<p>At devexhub, we help businesses navigate the complexities of implementing AI in transportation. Our expertise in AI integration and logistics optimization ensures that your organization can thrive in this new era of smart mobility. To talk through what a more reliable transportation model could look like for your team, reach out to devexhub.</p>

<h2>Frequently Asked Questions</h2>
<p><strong>What are the main benefits of AI in transportation?</strong> AI enhances traffic flow, reduces operational costs, and improves user experience through predictive analytics and real-time data management.</p>
<p><strong>How does AI impact logistics?</strong> AI optimizes routes, predicts demand, and manages inventory, leading to reduced costs and improved efficiency in logistics operations.</p>
<p><strong>Are there any downsides to implementing AI in transportation?</strong> Challenges include data privacy concerns, security risks, and the potential for job displacement in traditional roles.</p>
<p><strong>How can businesses prepare for AI integration?</strong> Businesses should invest in AI technologies, foster a culture of innovation, and collaborate with other sectors to create efficient transportation systems.</p>

<h2>Conclusion</h2>
<p>AI is revolutionizing transportation by making traffic management more efficient, logistics smarter, and mobility solutions more convenient. The future of transportation is bright, with AI at the forefront of this transformation. As organizations embrace these changes, they will not only enhance their operational efficiency but also contribute to a more sustainable and user-friendly transportation environment.</p>
<p>For those looking to stay ahead in this evolving landscape, explore devexhub's AI integration services to drive your transportation strategies forward. Let's work together to transform your operations into a model of efficiency and innovation.</p>"""

        return {
            "title": "AI's Role in Revolutionizing Transportation",
            "meta_description": "Explore how artificial intelligence is transforming traffic management, logistics, and smart mobility solutions for a more efficient future.",
            "category": "Technology",
            "tags": ["AI", "Transportation", "Logistics", "Smart Mobility"],
            "excerpt": "Imagine a world where traffic jams are a thing of the past. Discover how artificial intelligence is transforming traffic management, logistics, and smart mobility solutions.",
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
                    "meta_title": {"type": "STRING"},
                    "meta_description": {"type": "STRING"},
                    "category": {"type": "STRING"},
                    "tags": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    },
                    "excerpt": {"type": "STRING"},
                    "body": {"type": "STRING"}
                },
                "required": ["title", "meta_title", "meta_description", "category", "tags", "excerpt", "body"]
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    
    try:
        usage = result.get('usageMetadata', {})
        prompt_tokens = usage.get('promptTokenCount', 0)
        completion_tokens = usage.get('candidatesTokenCount', 0)
        if prompt_tokens or completion_tokens:
            log_token_usage(None, 'blog_generation', 'gemini-1.5-flash', prompt_tokens, completion_tokens)
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
        usage = result.get('usageMetadata', {})
        prompt_tokens = usage.get('promptTokenCount', 0)
        completion_tokens = usage.get('candidatesTokenCount', 0)
        if prompt_tokens or completion_tokens:
            log_token_usage(None, 'social_generation', 'gemini-1.5-flash', prompt_tokens, completion_tokens)
        text_content = result['candidates'][0]['content']['parts'][0]['text']
        content = json.loads(text_content.strip())
        content['generation_prompt'] = user_prompt
        content['ai_model'] = 'gemini-1.5-flash'
        return content
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Failed to parse Gemini response: {e}")
        raise ValueError("Invalid response format from Gemini")


# ─────────────────────────────────────────────────────────────────────────────
# BLOG VISUAL ELEMENTS INJECTOR
# ─────────────────────────────────────────────────────────────────────────────

def _upload_bytes_to_imgbb(image_bytes: bytes, name: str) -> str:
    """Uploads raw image bytes to imgbb and returns the permanent public URL."""
    import base64, requests as _req
    from decouple import config as _cfg
    imgbb_key = _cfg('IMGBB_API_KEY', default='')
    if not imgbb_key:
        logger.warning("IMGBB_API_KEY not set — cannot upload infographic.")
        return ""
    try:
        b64 = base64.b64encode(image_bytes).decode('utf-8')
        resp = _req.post(
            'https://api.imgbb.com/1/upload',
            data={'key': imgbb_key, 'image': b64, 'name': name},
            timeout=30
        )
        if resp.status_code == 200:
            url = resp.json().get('data', {}).get('url', '')
            if url:
                logger.info(f"Infographic uploaded to imgbb: {url}")
                return url
    except Exception as e:
        logger.warning(f"imgbb upload error: {e}")
    return ""


def _generate_infographic_image(description: str, topic: str) -> str:
    """
    Generates an infographic image via gpt-image-1-mini and uploads to imgbb.
    Returns the permanent public URL or empty string on failure.
    """
    import uuid, requests as _req, base64
    prompt = (
        f"Create a clean, professional, modern infographic for a B2B blog article. "
        f"Topic: '{topic}'. Visual focus: {description}. "
        f"Style: flat design, corporate color palette (deep blue, white, orange accents), "
        f"icon-based layout, clear typography, no stock photo backgrounds, no people. "
        f"Include a minimal diagram, icons, or labeled boxes that visually summarize the key concepts. "
        f"Make it look like a premium SaaS blog infographic. 16:9 widescreen layout."
    )
    try:
        logger.info(f"Generating infographic image: {description[:80]}")
        response = client.images.generate(
            model="gpt-image-1-mini",
            prompt=prompt,
            n=1,
            size="1536x1024"
        )
        img_bytes = None
        b64_data = getattr(response.data[0], 'b64_json', None)
        generated_url = response.data[0].url if response.data else None
        if b64_data:
            img_bytes = base64.b64decode(b64_data)
        elif generated_url:
            r = _req.get(generated_url, timeout=20)
            if r.status_code == 200:
                img_bytes = r.content
        if img_bytes:
            name = f"cadence_infographic_{uuid.uuid4().hex[:8]}"
            return _upload_bytes_to_imgbb(img_bytes, name)
    except Exception as e:
        logger.warning(f"Infographic image generation failed: {e}")
    return ""


def _render_cta_banner(website) -> str:
    """Returns a fully styled HTML CTA banner block linking to website's contact page."""
    contact_url = f"{(website.url or '').rstrip('/')}/contact/"
    site_name = website.name or "Us"
    industry = website.industry or "business"
    cta_text = f"Ready to see how {site_name} can help your {industry}?"
    return f"""
<div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);
            border-radius:14px;padding:36px 44px;margin:44px 0;
            display:flex;align-items:center;justify-content:space-between;
            flex-wrap:wrap;gap:20px;box-shadow:0 8px 32px rgba(0,0,0,0.18);">
  <div>
    <p style="color:#ffffff;font-size:20px;font-weight:700;margin:0 0 6px;line-height:1.3;">
      {cta_text}
    </p>
    <p style="color:#94a3b8;margin:0;font-size:15px;">
      Talk to our team — no commitment needed.
    </p>
  </div>
  <a href="{contact_url}" target="_blank"
     style="background:#f97316;color:#ffffff;padding:14px 28px;border-radius:8px;
            font-weight:700;text-decoration:none;white-space:nowrap;
            display:inline-block;font-size:15px;letter-spacing:0.3px;">
    Contact Us →
  </a>
</div>"""


def _render_step_diagram(steps_raw: str) -> str:
    """Converts 'Step1|Step2|Step3' pipe-separated string to styled HTML step flow."""
    steps = [s.strip() for s in steps_raw.split('|') if s.strip()]
    accent_colors = ['#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#ef4444', '#06b6d4']
    items_html = ""
    for i, step in enumerate(steps):
        color = accent_colors[i % len(accent_colors)]
        items_html += f"""
  <div style="background:#ffffff;border-radius:12px;padding:22px 16px;
              flex:1;min-width:130px;max-width:200px;text-align:center;
              border-top:4px solid {color};
              box-shadow:0 2px 10px rgba(0,0,0,0.07);">
    <div style="font-size:28px;font-weight:900;color:{color};line-height:1;">{str(i+1).zfill(2)}.</div>
    <div style="font-weight:700;margin-top:10px;font-size:14px;color:#1e293b;line-height:1.4;">{step}</div>
  </div>"""
    return f"""
<div style="display:flex;gap:12px;margin:36px 0;flex-wrap:wrap;justify-content:center;
            align-items:stretch;">
{items_html}
</div>"""


def _render_infographic_block(img_url: str, caption: str) -> str:
    """Returns an HTML figure block embedding the infographic."""
    return f"""
<figure style="margin:40px 0;text-align:center;">
  <img src="{img_url}" alt="{caption}"
       style="max-width:100%;border-radius:14px;
              box-shadow:0 6px 24px rgba(0,0,0,0.12);display:block;margin:0 auto;" />
  <figcaption style="color:#64748b;font-size:13px;margin-top:10px;font-style:italic;">
    {caption}
  </figcaption>
</figure>"""


def inject_visual_elements(body: str, website, topic: str) -> str:
    """
    Post-processes a generated blog HTML body and replaces special markers with
    rich visual elements:
      - <!-- CADENCE_CTA --> → styled promotional CTA banner
      - <!-- CADENCE_STEPS: Step1|Step2|Step3 --> → numbered step flow diagram
      - <!-- CADENCE_INFOGRAPHIC: description --> → AI-generated image from gpt-image-1-mini
    """
    import re

    # 1. Replace CTA markers
    body = re.sub(
        r'<!--\s*CADENCE_CTA\s*-->',
        _render_cta_banner(website),
        body,
        flags=re.IGNORECASE
    )

    # 2. Replace step diagram markers
    def _replace_steps(m):
        return _render_step_diagram(m.group(1))
    body = re.sub(
        r'<!--\s*CADENCE_STEPS:\s*([^>]+?)\s*-->',
        _replace_steps,
        body,
        flags=re.IGNORECASE
    )

    # 3. Replace infographic markers (generate image per marker)
    def _replace_infographic(m):
        description = m.group(1).strip()
        img_url = _generate_infographic_image(description, topic)
        if img_url:
            return _render_infographic_block(img_url, description)
        # Fallback: remove the marker silently if image gen fails
        logger.warning(f"Infographic generation failed for: {description[:60]}")
        return ""

    body = re.sub(
        r'<!--\s*CADENCE_INFOGRAPHIC:\s*([^>]+?)\s*-->',
        _replace_infographic,
        body,
        flags=re.IGNORECASE
    )

    return body


def generate_blog_post(idea: ContentIdea, website: Website) -> dict:
    """Generates a full blog post using a single prompt approach."""
    # Get live search data
    logger.info(f"Performing live search for topic: {idea.title}")
    live_data = search_live_data(idea.title)
    
    # Get user-uploaded samples (NOT from crawler)
    style_reference = get_style_reference_samples(website, 'blog')

    target_keywords = (
        ", ".join(idea.meta_tags)
        if idea.meta_tags
        else "Auto-select relevant keywords"
    )

    system_prompt = build_system_prompt(website, 'blog')
    import json
    user_prompt = f"""
You are a senior content strategist, editor, SEO specialist, and B2B writer.

Write an ORIGINAL, human-written blog post for {website.name} ({website.domain}).

====================
INPUT DETAILS
====================
Topic: {idea.title}
Context: {idea.context or "None provided"}
Target Keywords: {target_keywords}

Reference Samples:
{style_reference}

Verified Search Data:
{live_data}

====================
WRITING DIRECTIVES (TO SOUND HUMAN-WRITTEN)
====================

1. Grounded in Execution & Practical Insight:
   - Write from operational experience rather than general explanation. The article should prioritize usefulness over theoretical completeness. Leave simple, obvious concepts unexplained if the target audience (practitioners) would already know them.
   - Address actual tradeoffs, operational constraints, decisions, and outcomes. Focus on real-world workflow bottlenecks, implementation friction, or common recurring mistakes.
   - Absolutely do NOT claim direct personal experience (avoid "in my experience", "I have found", "my team discovered", "over the years"). Focus on explaining common patterns and choices from an objective but deeply knowledgeable perspective.

2. Tone, Style & Pacing:
   - Use clear, plain, conversational B2B English. Vary paragraph and sentence lengths dramatically—mix very short, punchy sentences with longer ones. Use occasional single-sentence paragraphs.
   - Strictly avoid AI clichés, corporate buzzwords, and marketing fluff. Do NOT use words like: leverage, optimize, enhance, transform, facilitate, streamline, robust, innovation, impactful, cutting-edge, powerful, seamless, revolutionize, groundbreaking, synergy, enable, empower, accelerate, redefine, or next-generation.
   - Keep transitions completely natural. Do NOT start paragraphs or sections with generic AI transitions like: "Furthermore", "Moreover", "Ultimately", "On the other hand", "In conclusion", "Looking ahead", "In practical terms", "As a result", "Therefore", or "That said".

3. Headings & Structure:
   - Avoid educational or predictable headings like "Introduction", "Conclusion", "What is X", "Benefits of X", "Key Features", "Final Thoughts".
   - Instead, write editorial headings that reflect choices, operational realities, implementation lessons, or tradeoffs (e.g. "The Hidden Costs of...", "Tradeoffs in...", "Where Teams Repeatedly Stumble").
   - Allow sections to end abruptly when the point has been made. Do not force neat summaries or lessons at the end of every section.

4. SEO & Authority:
   - Integrate target keywords and semantically related terms naturally.
   - Use statistics, percentages, and reports ONLY if they are explicitly present in the "Verified Search Data" section above. Never fabricate statistics.

====================
OUTPUT
====================
Return ONLY valid JSON in the following format:
{{
    "title": "A practitioner-level, engaging title matching the style guide",
    "meta_title": "An SEO-friendly meta title under 60 characters, e.g. Title | Brand",
    "meta_description": "An engaging, natural SEO description under 160 characters",
    "category": "A relevant single-word or short phrase category (e.g., Marketing, Engineering)",
    "tags": ["tag1", "tag2"],
    "excerpt": "A brief 2-3 sentence overview of the article",
    "body": "Your full, deep-dive article content formatted in clean HTML. CRITICAL WORD COUNT: The body MUST be 900–1200 words minimum — count every word carefully before finishing. Use 5–6 detailed H2 sections with multiple paragraphs each. Allowed tags: h2, h3, p, ul, ol, li, strong, a, blockquote, figure, figcaption, div. VISUAL MARKERS — embed these HTML comments naturally inside the body at appropriate positions (do NOT place them all at the end): (1) Place exactly one '<!-- CADENCE_CTA -->' somewhere mid-article between two sections where a call-to-action fits naturally (e.g. after explaining a problem or benefit). (2) If the article describes a process, workflow, or sequential steps, place '<!-- CADENCE_STEPS: Step One Title|Step Two Title|Step Three Title|Step Four Title -->' immediately after the paragraph that introduces the steps — use 3 to 6 pipe-separated step labels. (3) Place exactly one '<!-- CADENCE_INFOGRAPHIC: brief description of what the infographic should visually show -->' after the second or third H2 section where a diagram or visual overview would benefit the reader most. Each marker must appear only once. Keep all markers on their own line between HTML elements."
}}
"""

#     user_prompt = f"""
# You are a senior content strategist, editor, and SEO writer.

# Write an ORIGINAL blog post for {website.name}.

# INPUT

# Topic: {idea.title}
# Context: {idea.context or "None provided"}
# Target Keywords: {target_keywords}

# Reference Samples:
# {style_reference}

# Verified Search Data:
# {live_data}

# GOAL

# Create an editorial-quality blog that feels written by an experienced human writer.

# Study the reference samples and learn:

# * tone
# * formatting
# * pacing
# * reading level
# * CTA placement

# Learn patterns only.
# Do not imitate wording.

# CONTENT

# * Length: 900–1300 words
# * Match search intent
# * Use clear H2/H3 headings
# * Keep paragraph lengths varied
# * Each section must contribute new information
# * Prefer practical insight over broad explanation
# * Use operational examples where useful
# * Explain ideas through situations, observations, and outcomes
# * Do not force examples into every section

# INTRODUCTION

# Start close to the reader's real problem.

# Choose one:

# * business observation
# * practical problem
# * realistic situation

# Do NOT begin with:

# * broad industry statements
# * definitions
# * future predictions
# * "In today's world"
# * "Every day, businesses..."
# * "AI is changing..."
# * "Imagine a world..."

# SECTION FLOW

# Do not use one fixed structure across the entire article.

# Different sections may use:

# * observation → explanation
# * problem → impact
# * example → learning
# * situation → outcome
# * insight → recommendation

# Some sections may:

# * be short
# * focus on one idea
# * skip examples

# Prioritize natural reading flow over perfect symmetry.

# Do NOT expose internal writing labels.

# Never output headings or phrases such as:

# * Situation
# * Explanation
# * Outcome
# * Insight
# * Example
# * Implementation Advice
# * Call to Action

# Use them internally only.

# SPECIFICITY

# Avoid generic actors:

# * a company
# * businesses
# * organizations

# Prefer:

# * teams
# * departments
# * workflows
# * operational situations

# Describe:

# * what changed
# * why it mattered
# * what happened next

# LANGUAGE

# Write in clear business English.

# Target approximately Grade 7–9 reading level.

# Prefer:

# * common words
# * shorter sentences
# * direct explanations

# If a simpler word works, use it.

# Avoid:

# * academic tone
# * motivational tone
# * corporate jargon
# * abstract language
# * dramatic technology framing

# Avoid repeated words such as:
# leverage
# optimize
# enhance
# transform
# facilitate
# streamline
# robust
# innovation
# impactful
# cutting-edge
# powerful
# seamless
# revolutionize
# significant
# groundbreaking

# AUTHORITY

# Use statistics only from Verified Search Data.

# Never invent numbers.

# If no verified data exists:
# use examples instead.

# SEO

# * Use target keywords naturally
# * Include related concepts naturally
# * Avoid keyword stuffing
# * Prioritize readability

# BRAND

# Mention {website.name} only if naturally relevant.
# Maximum one mention.

# CTA

# End with practical next steps.

# Do not sound promotional.

# OUTPUT

# Return ONLY valid JSON.

# {{
# "title":"",
# "meta_description":"",
# "category":"",
# "tags":[],
# "excerpt":"",
# "body":"clean HTML only"
# }}
# """

    try:
        content = call_llm(
            user_prompt,
            system_prompt=system_prompt,
            max_tokens=4000,
            temperature=0.7,
            json_mode=True,
            website=website,
            section='blog_generation'
        )
        content['generation_prompt'] = user_prompt
        content['ai_model'] = config('AI_MODEL', default='gpt-4o-mini')

        # Post-process: inject visual elements (CTA, step diagrams, infographics)
        raw_body = content.get('body', '')
        if raw_body:
            try:
                logger.info(f"Injecting visual elements for: {idea.title}")
                content['body'] = inject_visual_elements(raw_body, website, idea.title)
                logger.info('Visual element injection complete.')
            except Exception as viz_err:
                logger.warning(f"Visual injection failed (using raw body): {viz_err}")

        return content
    except Exception as e:
        logger.error(f"Failed to generate blog post with single prompt: {e}")
        fallback_content = get_rich_fallback_blog(idea.title)
        fallback_content['generation_prompt'] = user_prompt
        fallback_content['ai_model'] = 'local-fallback'
        return fallback_content

def generate_social_post(idea: ContentIdea, website: Website, platform: str) -> dict:
    """Generates platform-specific social media content using user-provided samples."""
    system_prompt = build_system_prompt(website, platform)
    
    # Get user-uploaded samples for this platform
    style_reference = get_style_reference_samples(website, platform)
    
    limits = {
        'instagram': '150-200 characters. Casual, emoji-rich. Include 3-5 relevant hashtags at the end of the post body.',
        'linkedin': '200-300 words. Professional tone. No emojis. Hook first line. Include 3-5 relevant hashtags at the end of the post body.',
        'youtube': '150-200 words. Include timestamps, subscribe CTA, and 3-5 relevant hashtags at the end of the post body.',
        'facebook': '100-150 words. Conversational. Include a question. Include 3-5 relevant hashtags at the end of the post body.',
        'twitter': '280 characters. Punchy. One insight. Include 1-2 relevant hashtags at the end.',
    }
    
    user_prompt = f"""Write a {platform.title()} post about "{idea.title}" for {website.name}.
 
 ================================================================================
 REFERENCE SAMPLES (Study these to understand the writing style)
 ================================================================================
 {style_reference}
 
 ================================================================================
 TASK DETAILS
 ================================================================================
 PLATFORM: {platform.title()}
 TOPIC: {idea.title}
 FORMAT RULES: {limits.get(platform, 'Platform-appropriate')}
 
 ================================================================================
 WRITING INSTRUCTIONS
 ================================================================================
 1. Study the reference samples to understand the style
 2. Write a {platform.title()} post that matches the EXACT style
 3. Follow the format rules
 4. Ensure the body text ends with 3-5 relevant hashtags based on the content (e.g. #WebDevelopment #Devexhub).
 5. Do NOT include any empty hashtags (like "#" or "# ") or malformed tags. Every hashtag must contain a real word.
 6. The "tags" array in the JSON output must contain these same hashtags (without the leading "#" symbol, e.g. ["WebDevelopment", "Devexhub"]).
 7. Return JSON with title, body, excerpt, tags
 
 ================================================================================
 OUTPUT FORMAT
 ================================================================================
 {{
   "title": "...(internal label)...",
   "body": "...(the actual post text)...",
   "excerpt": "...(same as body for social)...",
   "tags": ["hashtag1", "hashtag2"],
   "meta_description": ""
 }}
 """

    try:
        content = call_llm(
            user_prompt,
            system_prompt=system_prompt,
            max_tokens=600,
            temperature=0.8,
            json_mode=True,
            website=website,
            section='social_generation'
        )
        content['generation_prompt'] = user_prompt
        content['ai_model'] = config('AI_MODEL', default='gpt-4o-mini')
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
    logo_is_light = False
    
    def detect_luminance_from_bytes(img_bytes) -> bool:
        try:
            from PIL import Image
            import io
            with Image.open(io.BytesIO(img_bytes)) as limg:
                limg = limg.convert("RGBA")
                l_pixels = limg.load()
                l_w, l_h = limg.size
                l_r, l_g, l_b = 0, 0, 0
                l_count = 0
                l_step = max(1, l_w // 50)
                for ly in range(0, l_h, l_step):
                    for lx in range(0, l_w, l_step):
                        r, g, b, a = l_pixels[lx, ly]
                        if a > 30:
                            if r > 240 and g > 240 and b > 240:
                                continue
                            l_r += r
                            l_g += g
                            l_b += b
                            l_count += 1
                if l_count == 0:
                    for ly in range(0, l_h, l_step):
                        for lx in range(0, l_w, l_step):
                            r, g, b, a = l_pixels[lx, ly]
                            if a > 30:
                                l_r += r
                                l_g += g
                                l_b += b
                                l_count += 1
                if l_count > 0:
                    lum = 0.299 * (l_r / l_count) + 0.587 * (l_g / l_count) + 0.114 * (l_b / l_count)
                    return lum > 200
        except Exception:
            pass
        return False

    try:
        if logo_url:
            if logo_url.startswith('/static/'):
                rel_path = logo_url.replace('/static/', '')
                logo_path = os.path.join(settings.BASE_DIR, 'frontend', rel_path)
                print("DEBUG: logo_path 1 is", logo_path)
                if logo_path is not None and os.path.exists(logo_path):
                    ext = logo_path.split('.')[-1].lower()
                    with open(logo_path, 'rb') as f:
                        file_bytes = f.read()
                    encoded = base64.b64encode(file_bytes).decode('utf-8')
                    mime = f"image/{ext}" if ext != 'svg' else "image/svg+xml"
                    custom_logo_data_uri = f"data:{mime};base64,{encoded}"
                    logo_is_light = detect_luminance_from_bytes(file_bytes)
            elif logo_url.startswith('http://') or logo_url.startswith('https://'):
                resp = requests.get(logo_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                if resp.status_code == 200:
                    ext = logo_url.split('.')[-1].lower()
                    if ext not in ['svg', 'png', 'jpg', 'jpeg', 'gif']:
                        ext = 'png'
                    mime = f"image/{ext}" if ext != 'svg' else "image/svg+xml"
                    encoded = base64.b64encode(resp.content).decode('utf-8')
                    custom_logo_data_uri = f"data:{mime};base64,{encoded}"
                    logo_is_light = detect_luminance_from_bytes(resp.content)
    except Exception as logo_err:
        logger.warning(f"Failed to load logo_url: {logo_err}")
        
    if not custom_logo_data_uri:
        media_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media')
        try:
            for ext in ['svg', 'png', 'jpg', 'jpeg']:
                logo_path = os.path.join(media_dir, f'devexhub_logo.{ext}')
                print("DEBUG: logo_path 2 is", logo_path)
                if logo_path is not None and os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        file_bytes = f.read()
                    encoded = base64.b64encode(file_bytes).decode('utf-8')
                    mime = f"image/{ext}" if ext != 'svg' else "image/svg+xml"
                    custom_logo_data_uri = f"data:{mime};base64,{encoded}"
                    logo_is_light = detect_luminance_from_bytes(file_bytes)
                    break
        except Exception:
            pass
        
    if custom_logo_data_uri:
        card_fill = "#0f172a" if logo_is_light else "#ffffff"
        card_stroke = "#334155" if logo_is_light else "#cbd5e1"
        if theme == "theme3":
            logo_content_svg = f'<image href="{custom_logo_data_uri}" x="0" y="0" width="100" height="100"/>'
        else:
            logo_content_svg = f"""<rect x="-10" y="-10" width="120" height="120" rx="12" fill="{card_fill}" stroke="{card_stroke}" stroke-width="1" filter="url(#shadow)"/>
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


def choose_cta_text(title: str, category: str) -> str:
    t_lower = title.lower() if title else ""
    c_lower = category.lower() if category else ""
    
    if any(k in t_lower or k in c_lower for k in ["guide", "how to", "tutorial", "learn", "course", "what is"]):
        return "LEARN MORE"
    elif any(k in t_lower or k in c_lower for k in ["product", "feature", "pricing", "store", "buy", "order"]):
        return "GET DETAILS"
    elif any(k in t_lower or k in c_lower for k in ["analytics", "growth", "seo", "marketing", "business"]):
        return "EXPLORE MORE"
    elif any(k in t_lower or k in c_lower for k in ["about", "contact", "support", "help", "team"]):
        return "MORE INFO"
    else:
        ctas = ["READ MORE", "LEARN MORE", "EXPLORE MORE", "GET DETAILS", "MORE INFO"]
        idx = (len(title) + len(category or "")) % len(ctas)
        return ctas[idx]


def generate_dalle_prompt_via_gpt(title: str, category: str, excerpt: str, website=None, is_dark_logo=True) -> str:
    """Uses GPT-4o to write a highly creative, custom DALL-E 3 image generation prompt for the blog post."""
    cta_text = choose_cta_text(title, category)
    primary_color = "#0f172a"  # Slate/Dark Blue
    secondary_color = "#3b82f6"  # Royal Blue
    email = "info@devexhub.com"
    phone = "+91 98759 05952"
    domain = "devexhub.com"
    
    industry = "General"
    topics = "General content"
    all_colors = []
    
    if website:
        # Resolve brand colors cleanly
        if website.brand_colors and isinstance(website.brand_colors, list) and len(website.brand_colors) > 0:
            all_colors = website.brand_colors
            # Filter to find vibrant accent colors (non-neutrals)
            non_neutrals = []
            for c in all_colors:
                c_clean = c.lstrip('#')
                if len(c_clean) in [3, 6]:
                    try:
                        if len(c_clean) == 3:
                            c_clean = "".join(x*2 for x in c_clean)
                        r = int(c_clean[0:2], 16)
                        g = int(c_clean[2:4], 16)
                        b = int(c_clean[4:6], 16)
                        # Check if color has saturation (non-neutral) and isn't pure black/white
                        if max(r, g, b) - min(r, g, b) >= 30 and 15 < (0.299*r + 0.587*g + 0.114*b) < 240:
                            non_neutrals.append(c)
                    except ValueError:
                        pass
            
            if len(non_neutrals) > 0:
                primary_color = non_neutrals[0]
                if len(non_neutrals) > 1:
                    secondary_color = non_neutrals[1]
                else:
                    remaining = [c for c in all_colors if c != primary_color]
                    secondary_color = remaining[0] if remaining else primary_color
            else:
                primary_color = all_colors[0]
                secondary_color = all_colors[1] if len(all_colors) > 1 else all_colors[0]

        if website.domain:
            domain = website.domain.strip().rstrip('/')
        
        # Build email (use contact_email, or fallback to info@domain)
        if website.contact_email:
            email = website.contact_email
        else:
            email_domain = domain.replace('www.', '').split('/')[0]
            email = f"info@{email_domain}"
            
        # Avoid falling back to Devex Hub phone if website has no phone
        if website.contact_phone:
            phone = website.contact_phone
        else:
            phone = ""
            
        if website.industry:
            industry = website.industry
        if website.topics:
            topics = ", ".join(website.topics) if isinstance(website.topics, list) else str(website.topics)
            
    # Construct footer dynamically based on available fields
    footer_parts = []
    if email:
        footer_parts.append(email)
    if phone:
        footer_parts.append(phone)
    if domain:
        footer_parts.append(domain)
    footer_text = " | ".join(footer_parts)
    
    # Format brand colors description
    colors_desc = f"Primary: '{primary_color}', Secondary: '{secondary_color}'"
    if all_colors:
        colors_desc += f" (Full Palette: {', '.join(all_colors)})"

    # Brand contrast instruction based on logo brightness
    if is_dark_logo:
        contrast_instruction = (
            f"The company logo is dark-colored (like dark blue, purple, or black). Therefore, you MUST design the top-left safety zone "
            f"(the top-left 25% width and 20% height corner area of the banner) to be a clean, solid, very light-colored background "
            f"(e.g., bright off-white, extremely light pastel blue, or light warm gray gradient) that fades softly into the darker "
            f"brand background color '{primary_color}' towards the center. This creates a high-contrast light corner that ensures a dark logo placed "
            f"there is 100% visible and readable. There must be no text, illustrations, or graphics in this zone."
        )
    else:
        contrast_instruction = (
            f"The company logo is light-colored (white/silver). Therefore, you MUST design the top-left safety zone "
            f"(the top-left 25% width and 20% height corner area of the banner) to be a clean, solid, very deep and dark backdrop "
            f"(e.g., deep dark blue, slate charcoal, or dark navy) to provide excellent natural contrast for a white/light logo. "
            f"There must be no text, illustrations, or graphics in this zone."
        )

    prompt = f"""You are a professional creative director and graphic designer.
Your task is to write ONE highly detailed, descriptive DALL-E 3 prompt to generate a PREMIUM WEBSITE BLOG HERO BANNER.

You must design the banner specifically for this blog post:
- Blog Title: "{title}"
- Blog Category: "{category}"
- Blog Industry: "{industry}"
- Blog Excerpt: "{excerpt}"

CRITICAL BRANDING & COLOR DETAILS:
- Brand Colors to use: {colors_desc}
  * IMPORTANT: You MUST strictly design the entire visual using these website colors so it integrates seamlessly with the website's brand identity. The primary brand color '{primary_color}' (or deep slate/charcoal if primary is neutral) MUST be the dominant, primary background color of the entire banner, extending 100% all the way to the absolute edges of the image canvas. The secondary brand color '{secondary_color}' (and other accents) MUST be used ONLY as an accent color for smaller detail highlights (like the text highlights, the button color, or small lighting glows in the illustration). Under NO circumstances should the secondary brand color '{secondary_color}' be used as an outer border, frame, margin, or padding surrounding the main content. This avoids creating a harsh or high-contrast border frame and ensures the layout is premium and elegant.
- Contact Info: Do NOT write any contact details (email, phone, or website URL) on the banner. Leave the bottom area completely blank and clear.
- Call-To-Action (CTA) Text: "{cta_text}"

DALL-E 3 PROMPT GENERATION INSTRUCTIONS:
Generate a DALL-E 3 prompt describing a banner with the following layout, content, and quality requirements:

1. THE COMPOSITION & LAYOUT (INTEGRATED, FULL-BLEED & NO PADDING):
- Design a single, unified, continuous background that flows seamlessly from the left typography area into the right visual area.
- The background should be a soft, premium gradient, subtle texture, or atmospheric environment using the resolved primary brand color '{primary_color}' as the dominant backdrop.
- **STRICT FULL-BLEED / NO-PADDING REQUIREMENT**: The image must be completely borderless, edge-to-edge, and full-bleed. The primary background color and design elements must extend all the way to the absolute boundaries of the image canvas. Under NO circumstances should there be any outer dark or light margins, empty space borders, padding, rounded corners for the outer image, shadows around the edges, or frame borders around the canvas. The background must cover 100% of the image space. There must be absolutely no outer colored frame (e.g., no gold or yellow outer border padding) surrounding the central content card. The main background must extend fully to all four edges of the image file.
- **NO CARDS OR CONTAINERS**: Do NOT draw any cards, containers, panels, device frames, laptop screens, or rounded-corner boxes to hold the text or the illustration. All text and illustrations must reside directly on the main continuous canvas background, completely unframed and borderless.
- **EXPANDED HERO VISUAL**: The visual illustration on the right side must be extremely large, bold, and cover-filling. It should occupy at least 60-70% of the banner space (right side and extending into the center), rather than being a small isolated graphic. The background elements of this illustration should flow and blend seamlessly into the left side behind the text.
- Left side: A spacious area for text with excellent readability, achieved through light gradients, depth, and negative space.
- Right side: A cinematic, high-end 3D illustration, isometric scene, or stylized visual metaphor that represents the core idea of the article.
- Elements from the right side (lighting, shadows, gradients, shapes, particles, or reflections) should subtly extend or blend into the left side, creating a natural visual flow.
- **DYNAMIC VISUAL METAPHOR POLICY**: Brainstorm a highly relevant, creative, and engaging visual metaphor for the right side based on the blog title "{title}", industry "{industry}", and excerpt "{excerpt}". Do NOT default to generic laptop mockups, desktop monitors, or stacks of screens unless the article is strictly a tutorial or product feature release for a specific software, dashboard, or mobile app.
- **CONDITIONAL RULE FOR COMPARISONS**: If the title "{title}" implies a comparison (e.g., SEO vs AEO vs GEO, or A vs B), design the right-side illustration as a LEFT vs RIGHT comparison that blends seamlessly at the center. Use contrasting visual themes, lighting, and symbols on each side with a soft, integrated transition in the middle—avoid any hard dividing line.

2. THE TYPOGRAPHY & RICH TEXT DENSITY (LEFT SIDE):
- **COMPACT HEADLINE SIZE & PUSHED-DOWN LAYOUT (OVERLAP PREVENTION)**: Write a shortened, punchy version of the title (maximum 3-4 words based on "{title}") in a medium-sized, compact, elegant, and highly readable geometric sans-serif typeface. The text must NOT be overly large or loud. PUSH all text down so that it starts strictly below the 20% height mark, keeping the top-left safety zone completely clear and avoiding any logo overlap.
- Subtitle: Generate a short, compelling subtitle (maximum 8-10 words) that highlights the core value or benefit. Render it clearly under the headline.
- **BODY DESCRIPTION / PARAGRAPH TEXT**: Beneath the subtitle, include a detailed, informative, and clean block of body text/paragraph (about 25-30 words, or 2-3 lines based on the blog excerpt: "{excerpt}") to give premium context. Ensure this text has excellent readability and spacing, making it look like a high-end corporate editorial magazine layout.
- Typography should be high contrast, crisp, and easy to read, with excellent hierarchy and spacing.
- CTA Section: Include a modern, rounded pill-shaped button at the bottom of the text panel that says "{cta_text}" with a small arrow/chevron icon (->), styled in the accent color.

3. BRAND INTEGRATION & EMPTY SPACES:
- **STRICT LOGO SAFETY ZONE**: The entire top-left area of the banner (specifically from the top-left corner down to 20% of the height and extending to 25% of the width) MUST be completely empty, blank, and contain only the flat background color. {contrast_instruction} The headline/title text must begin strictly below this 20% height line, ensuring it never overlaps the company logo.
- **NO CATEGORY TEXT OR EXTRA HEADERS**: Under no circumstances should you write the category name ("{category}") or any other labels, tags, or small text headers anywhere on the banner. The category name "{category}" must be completely absent from the image. Do NOT write the word "{category}" or depict any category label under the logo or anywhere on the banner. Keep the top-left safety zone completely clean and free of all text.
- Do NOT write any text or render a logo in this area.
- Footer: Do NOT write any text, phone number, email, or website URL at the bottom of the banner. Keep the bottom 15% of the banner completely blank and empty (solid background only) so that we can overlay a custom footer bar later in post-processing.

4. VISUAL STYLE & ATMOSPHERE (EYE-CATCHING & CINEMATIC):
- The banner must be visually striking, cinematic, and emotionally engaging within the first second.
- Use dramatic yet balanced lighting, depth, and atmosphere to create a sense of scale and storytelling.
- The right-side hero visual should be the focal masterpiece—premium 3D, ultra-detailed, and intelligently symbolic.
- Use premium materials such as glassmorphism, soft-touch surfaces, metallic accents, acrylics, glowing edges, volumetric light, reflections, and ambient occlusion.
- Ensure the overall color grading, contrast, and composition feel like a magazine cover or high-end campaign.
- The banner should spark curiosity and motivate readers to click and read the article.
- **STRICTLY AVOID**: Card-in-card designs, rounded outer canvas frames, margins or padded borders around the image, clipart aesthetics, generic stock illustrations, multiple laptops, multiple monitors, random dashboards, flat icon collections, cartoon styles, busy compositions, visual clutter, low-detail objects, meme aesthetics, gaming-inspired visuals, excessive symmetry, placeholder graphics, cheap gradients, overused AI visual tropes, floating unrelated elements, corporate handshake imagery, people pointing at screens, generic office scenes, generic 3D robot/AI characters with glowing eyes, and simple stock-icon visual trees.
- Every visual decision must feel intentional and professionally art-directed.

5. RENDER QUALITY & TECHNICAL DETAILS:
- Ultra-high detail, 8K quality, professional 3D rendering.
- Smooth gradients, perfect typography, realistic materials, soft shadows, depth of field, and cinematic composition.
- The final image should look like a premium website hero banner designed by a world-class creative agency.
- Quality references to draw design inspiration from: Apple keynote visuals, Stripe editorial campaigns, Linear brand illustrations, Notion marketing design, Airbnb storytelling graphics, IBM Think conference branding, Deloitte technology reports, Behance award-winning digital artwork.

Output ONLY the final DALL-E 3 prompt. Do not add any extra explanation or markdown formatting."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=600,
            temperature=0.7,
        )
        if hasattr(response, 'usage') and response.usage:
            log_token_usage(website, 'prompt_engineering', MODEL, response.usage.prompt_tokens, response.usage.completion_tokens)
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Failed to generate custom DALL-E prompt using GPT: {e}")
        return f"A premium, professional, modern corporate blog banner for '{title}' (Category: {category}). {excerpt}. Clean typography on the left with title, description, and button. Beautiful illustration representing the topic on the right. Top-left area is empty. Clean, eye-catching, modern design."


def generate_svg_cover_via_gpt(title: str, category: str, excerpt: str = "", website=None) -> tuple:
    """
    Generates a high-quality blog cover banner using the 'gpt-image-1-mini' model for full visual generation
    (including custom background, typography, illustration, and button) and then composites the company logo
    onto the top-right corner using Pillow before wrapping it in a minimal SVG wrapper.
    """
    import os
    import uuid
    import base64
    import requests
    from django.conf import settings
    from PIL import Image, ImageDraw

    # Extract corporate logo dynamically if website is provided (done first to check contrast requirements)
    logo_file_path = None
    try:
        logo_url = website.logo_url if website else ""
        if logo_url:
            if logo_url.startswith('/static/'):
                rel_path = logo_url.replace('/static/', '')
                logo_path = os.path.join(settings.BASE_DIR, 'frontend', rel_path)
                if os.path.exists(logo_path):
                    logo_file_path = logo_path
            elif logo_url.startswith('http://') or logo_url.startswith('https://'):
                resp = requests.get(logo_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                if resp.status_code == 200:
                    ext = logo_url.split('.')[-1].lower()
                    if ext not in ['svg', 'png', 'jpg', 'jpeg', 'gif']:
                        ext = 'png'
                    media_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media')
                    temp_logo_path = os.path.join(media_dir, f'temp_logo_{uuid.uuid4().hex}.{ext}')
                    with open(temp_logo_path, 'wb') as f:
                        f.write(resp.content)
                    logo_file_path = temp_logo_path
    except Exception as logo_err:
        logger.warning(f"Failed to load logo_url in generate_svg_cover_via_gpt: {logo_err}")

    if not logo_file_path:
        media_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media')
        try:
            for ext in ['svg', 'png', 'jpg', 'jpeg']:
                logo_path = os.path.join(media_dir, f'devexhub_logo.{ext}')
                if os.path.exists(logo_path):
                    logo_file_path = logo_path
                    break
        except Exception:
            pass

    # Determine if the logo is primarily dark or light to instruct DALL-E to adjust the background color accordingly
    is_dark_logo = True
    if logo_file_path and os.path.exists(logo_file_path):
        try:
            logo_img = Image.open(logo_file_path).convert("RGBA")
            lw, lh = logo_img.size
            l_pixels = logo_img.load()
            t_r, t_g, t_b, t_cnt = 0, 0, 0, 0
            for ly in range(lh):
                for lx in range(lw):
                    r, g, b, a = l_pixels[lx, ly]
                    if a > 40:
                        if r > 240 and g > 240 and b > 240:
                            continue
                        t_r += r
                        t_g += g
                        t_b += b
                        t_cnt += 1
            if t_cnt == 0:
                for ly in range(lh):
                    for lx in range(lw):
                        r, g, b, a = l_pixels[lx, ly]
                        if a > 40:
                            t_r += r
                            t_g += g
                            t_b += b
                            t_cnt += 1
            if t_cnt > 0:
                avg_r = t_r / t_cnt
                avg_g = t_g / t_cnt
                avg_b = t_b / t_cnt
                logo_lum = 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b
                if logo_lum >= 140:
                    is_dark_logo = False
        except Exception as lum_err:
            logger.warning(f"Could not compute logo luminance: {lum_err}")

    # 1. Generate dynamic, highly descriptive DALL-E prompt based on title/content using GPT-4o
    image_prompt = generate_dalle_prompt_via_gpt(title, category, excerpt, website=website, is_dark_logo=is_dark_logo)
    logger.info(f"Custom DALL-E prompt generated (is_dark_logo={is_dark_logo}): {image_prompt[:200]}...")

    b64_data = ""
    try:
        logger.info(f"Calling client.images.generate using gpt-image-1 for full banner...")
        response = client.images.generate(
            model="gpt-image-1-mini",
            prompt=image_prompt,
            n=1,
            size="1536x1024"
        )
        log_token_usage(website, 'image_generation', 'dall-e-3', 0, 0)
        generated_url = response.data[0].url
        b64_data = getattr(response.data[0], 'b64_json', None)

        raw_img_bytes = None
        if b64_data:
            logger.info("gpt-image-1 returned base64 data. Decoding...")
            raw_img_bytes = base64.b64decode(b64_data)
        elif generated_url:
            logger.info("gpt-image-1 response received as URL. Downloading image...")
            img_resp = requests.get(generated_url, timeout=15)
            if img_resp.status_code == 200:
                raw_img_bytes = img_resp.content

        if raw_img_bytes:
            media_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media')
            os.makedirs(media_dir, exist_ok=True)
            temp_filename = f"temp_cover_{uuid.uuid4().hex}.png"
            temp_filepath = os.path.join(media_dir, temp_filename)
            with open(temp_filepath, 'wb') as f:
                f.write(raw_img_bytes)

            # Composite the logo and draw footer using Pillow
            try:
                bg = Image.open(temp_filepath).convert("RGBA")
                bg_w, bg_h = bg.size
                
                # Create a single transparent overlay for all programmatic shapes and text
                overlay = Image.new("RGBA", bg.size, (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                
                # 1. Overlay the logo if it exists
                if logo_file_path and os.path.exists(logo_file_path):
                    try:
                        logo = Image.open(logo_file_path).convert("RGBA")
                        logo_w, logo_h = logo.size
                        
                        # Remove solid white background from the logo using flood-fill from corners
                        corners = [logo.getpixel((0, 0)), logo.getpixel((logo_w - 1, 0)), 
                                   logo.getpixel((0, logo_h - 1)), logo.getpixel((logo_w - 1, logo_h - 1))]
                        is_white_bg = any(p[0] > 230 and p[1] > 230 and p[2] > 230 and p[3] > 100 for p in corners)
                        if is_white_bg:
                            try:
                                for corner in [(0, 0), (logo_w - 1, 0), (0, logo_h - 1), (logo_w - 1, logo_h - 1)]:
                                    p = logo.getpixel(corner)
                                    if p[0] > 220 and p[1] > 220 and p[2] > 220 and p[3] > 100:
                                        ImageDraw.floodfill(logo, corner, (255, 255, 255, 0), thresh=45)
                                logger.info("Successfully converted logo white background to transparent.")
                            except Exception as flood_err:
                                logger.warning(f"Failed to floodfill logo background: {flood_err}")

                        # Resize logo: height is 11% of background height
                        new_h = int(bg_h * 0.11)
                        new_w = int(logo_w * (new_h / logo_h))
                        logo_resized = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        
                        # Coordinates in top-left with margins
                        margin_x = int(bg_w * 0.05)
                        margin_y = int(bg_h * 0.05)
                        paste_x = margin_x
                        paste_y = margin_y
                        
                        # Sample background color in the logo area to determine luminance
                        logo_bg_crop = bg.crop((margin_x, margin_y, margin_x + new_w, margin_y + new_h))
                        logo_bg_avg = logo_bg_crop.resize((1, 1)).convert("RGB")
                        logo_bg_r, logo_bg_g, logo_bg_b = logo_bg_avg.getpixel((0, 0))
                        logo_bg_lum = 0.299 * logo_bg_r + 0.587 * logo_bg_g + 0.114 * logo_bg_b
                        
                        # Fallback check: only apply glow if logo color clashes with background color
                        need_glow = False
                        glow_color = None
                        
                        if is_dark_logo:
                            # Dark logo on dark background is not visible -> needs white glow fallback
                            if logo_bg_lum < 75:
                                need_glow = True
                                glow_color = (255, 255, 255, 140)  # 55% opacity white halo
                        else:
                            # Light logo on light background is not visible -> needs dark glow fallback
                            if logo_bg_lum >= 120:
                                need_glow = True
                                glow_color = (0, 0, 0, 80)          # 31% opacity dark shadow
                                
                        if need_glow and glow_color:
                            from PIL import ImageFilter
                            alpha = logo_resized.split()[3]
                            
                            # Expand the alpha mask by shifting in 8 directions (dilation)
                            glow_mask = Image.new("L", logo_resized.size, 0)
                            for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (-2, 0), (2, 0), (0, -2), (0, 2)]:
                                glow_mask.paste(alpha, (dx, dy), alpha)
                                
                            # Soften/blur the expanded glow mask
                            glow_mask_blurred = glow_mask.filter(ImageFilter.GaussianBlur(2))
                            
                            # Create solid color image with glow color and apply blurred alpha mask
                            glow_img = Image.new("RGBA", logo_resized.size, glow_color)
                            glow_img.putalpha(glow_mask_blurred)
                            
                            # Composite the glow shadow onto overlay
                            overlay.alpha_composite(glow_img, (paste_x, paste_y))
                            logger.info("Luminance contrast is low: applied fallback contour halo glow/shadow.")

                        # Always composite the original transparent logo on top
                        overlay.alpha_composite(logo_resized, (paste_x, paste_y))
                        logger.info("Successfully pasted company logo onto overlay.")
                    except Exception as logo_err:
                        logger.warning(f"Failed to overlay logo: {logo_err}")

                # 2. Draw the programmatic footer bar using an alpha overlay to prevent alpha flattening issues
                try:
                    # Resolve contact info
                    email = "info@devexhub.com"
                    phone = "+91 98759 05952"
                    domain = "devexhub.com"
                    
                    if website:
                        if website.domain:
                            domain = website.domain.strip().rstrip('/')
                        if website.contact_email:
                            email = website.contact_email
                        else:
                            email_domain = domain.replace('www.', '').split('/')[0]
                            email = f"info@{email_domain}"
                        if website.contact_phone:
                            phone = website.contact_phone
                        else:
                            phone = ""

                    footer_parts = []
                    if email:
                        footer_parts.append(email)
                    if phone:
                        footer_parts.append(phone)
                    if domain:
                        footer_parts.append(domain)
                    footer_text = " | ".join(footer_parts)

                    # Sample pixels in the footer area to determine luminance
                    footer_crop_y0 = int(bg_h * 0.91)
                    footer_crop_y1 = int(bg_h * 0.98)
                    footer_pixels = bg.crop((int(bg_w * 0.1), footer_crop_y0, int(bg_w * 0.9), footer_crop_y1))
                    
                    # Get average color of the footer area
                    avg_color_img = footer_pixels.resize((1, 1)).convert("RGB")
                    avg_r, avg_g, avg_b = avg_color_img.getpixel((0, 0))
                    luminance = 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b
                    
                    # Colors for the glassmorphism footer bar
                    if luminance < 120:  # Dark background
                        bar_fill = (255, 255, 255, 30)       # Glassmorphism light overlay (12% opacity)
                        bar_outline = (255, 255, 255, 55)    # 22% opacity white border
                        text_fill = (255, 255, 255, 235)     # 92% opacity white text
                    else:  # Light background
                        bar_fill = (15, 23, 42, 25)          # Glassmorphism dark overlay (10% opacity)
                        bar_outline = (15, 23, 42, 50)       # 20% opacity dark border
                        text_fill = (15, 23, 42, 225)        # 88% opacity dark text

                    # Footer bar dimensions (rounded card at the bottom)
                    bar_w = int(bg_w * 0.90) # 90% of image width
                    bar_h = int(bg_h * 0.07) # 7% of image height
                    
                    bar_x0 = int((bg_w - bar_w) / 2)
                    bar_x1 = bar_x0 + bar_w
                    
                    # Position it lower, right at the bottom area (91% height mark)
                    bar_y0 = int(bg_h * 0.91)
                    bar_y1 = bar_y0 + bar_h
                    
                    # Draw rounded bar on overlay
                    overlay_draw.rounded_rectangle([bar_x0, bar_y0, bar_x1, bar_y1], radius=12, fill=bar_fill, outline=bar_outline, width=2)
                    
                    # Draw text on overlay in the middle
                    from PIL import ImageFont
                    font_size = int(bar_h * 0.40) # Font size is 40% of the bar's height
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except Exception:
                        try:
                            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
                        except Exception:
                            try:
                                font = ImageFont.load_default(size=font_size)
                            except Exception:
                                font = ImageFont.load_default()
                            
                    # Calculate text size and center it
                    text_str = footer_text
                    try:
                        t_w = overlay_draw.textlength(text_str, font=font)
                        t_h = font_size
                    except Exception:
                        t_w = len(text_str) * (font_size * 0.6)
                        t_h = font_size
                        
                    text_x = int(bar_x0 + (bar_w - t_w) / 2)
                    text_y = int(bar_y0 + (bar_h - t_h) / 2 - (font_size * 0.05))
                    
                    overlay_draw.text((text_x, text_y), text_str, fill=text_fill, font=font)
                    logger.info("Successfully drew custom programmatic footer bar.")
                except Exception as footer_err:
                    logger.warning(f"Failed to draw custom footer bar: {footer_err}")

                # Composite the single overlay onto the original image
                bg = Image.alpha_composite(bg, overlay)
                
                # Save final composed image back as optimized JPEG (90% size reduction)
                bg.convert("RGB").save(temp_filepath, "JPEG", quality=85, optimize=True)
                logger.info("Successfully composited logo and footer onto JPEG.")
            except Exception as composite_err:
                logger.warning(f"Failed to composite using Pillow: {composite_err}")

            # Read back composed image
            with open(temp_filepath, 'rb') as f:
                composed_bytes = f.read()
            b64_data = base64.b64encode(composed_bytes).decode('utf-8')
            
            # Save final filename as .jpg
            final_filename = f"blog_cover_full_{uuid.uuid4().hex}.jpg"
            final_filepath = os.path.join(media_dir, final_filename)
            os.rename(temp_filepath, final_filepath)
            logger.info(f"Successfully saved final composed JPEG to: {final_filepath}")

    except Exception as img_err:
        logger.warning(f"gpt-image-1 generation failed: {img_err}. Falling back to standard SVG template planning.")

    # 3. If generated successfully, wrap the final PNG base64 in a minimal SVG wrapper
    if b64_data:
        svg = f"""<svg width="1200" height="800" viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg">
  <image href="data:image/png;base64,{b64_data}" x="0" y="0" width="1200" height="800"/>
</svg>"""
        return svg, final_filename

    # Fallback to normal layout planning if gpt-image-1 failed
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
        if hasattr(response, 'usage') and response.usage:
            log_token_usage(website, 'visual_strategy', MODEL, response.usage.prompt_tokens, response.usage.completion_tokens)
        data = json.loads(response.choices[0].message.content.strip())
        svg_content = build_svg_from_data(data, website=website)
        if svg_content:
            return svg_content, None
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
            "cta_text": choose_cta_text(title, category),
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
        return build_svg_from_data(fallback_data, website=website), None
    except Exception as fallback_err:
        logger.error(f"Fallback SVG generation also failed: {fallback_err}")
    return "", None


def generate_for_idea(idea_id: int, generate_image: bool = True):
    """Main entry point called by Celery task."""
    from .models import ContentIdea, ContentDraft
    
    idea = ContentIdea.objects.select_related('website').get(pk=idea_id)
    
    # Strip any starting numbers (e.g. "1. Topic") from the title
    import re
    cleaned_title = re.sub(r'^\d+\s*\.\s*', '', idea.title).strip()
    if cleaned_title != idea.title:
        idea.title = cleaned_title
        idea.save()
        
    website = idea.website
    
    try:
        cover_image_url = ""
        category_name = ""
        if idea.platform == 'blog':
            content_data = generate_blog_post(idea, website)
            category_name = content_data.get('category', 'General')
        else:
            content_data = generate_social_post(idea, website, idea.platform)
            category_name = website.industry or 'Social Media'
            
        # Generate cover image using GPT (SVG vector art)
        if generate_image:
            try:
                from django.conf import settings
                import os
                import uuid
                
                logger.info(f"Generating GPT SVG cover image for {idea.platform}: {idea.title}")
                svg_code, png_filename = generate_svg_cover_via_gpt(
                    idea.title, 
                    category_name, 
                    excerpt=content_data.get('excerpt', ''), 
                    website=website
                )
                
                if png_filename:
                    cover_image_url = f"/static/media/{png_filename}"
                    logger.info(f"Successfully generated and saved GPT PNG cover image to: {cover_image_url}")
                elif svg_code:
                    media_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media')
                    os.makedirs(media_dir, exist_ok=True)
                    
                    filename = f"cover_{uuid.uuid4().hex}.svg"
                    filepath = os.path.join(media_dir, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(svg_code)
                        
                    cover_image_url = f"/static/media/{filename}"
                    logger.info(f"Successfully generated and saved GPT SVG cover image to: {cover_image_url}")
            except Exception as img_err:
                logger.warning(f"Failed to generate GPT SVG cover image: {img_err}")
        
        draft = ContentDraft.objects.create(
            idea=idea,
            website=website,
            platform=idea.platform,
            title=content_data.get('title', idea.title),
            body=content_data.get('body', ''),
            excerpt=content_data.get('excerpt', ''),
            meta_description=content_data.get('meta_description', ''),
            meta_title=content_data.get('meta_title', content_data.get('title', idea.title)),
            tags=content_data.get('tags', []),
            ai_model=content_data.get('ai_model', MODEL),
            generation_prompt=content_data.get('generation_prompt', ''),
            status='draft',
            cover_image=cover_image_url,
            category=category_name,
        )
        
        # Inject internal links automatically
        try:
            from .utils import inject_internal_links
            inject_internal_links(draft)
        except Exception as link_err:
            logger.warning(f"Failed to inject internal links on success: {link_err}")
            
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
                meta_title=title_val,
                tags=tags,
                ai_model='local-fallback',
                generation_prompt='Simulated Prompt (OpenAI Fallback)',
                status='draft',
                cover_image="",
                category=category_name,
            )
            
            # Inject internal links automatically
            try:
                from .utils import inject_internal_links
                inject_internal_links(draft)
            except Exception as link_err:
                logger.warning(f"Failed to inject internal links on fallback: {link_err}")
                
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
        return call_llm(
            prompt,
            max_tokens=600,
            temperature=0.3,
            json_mode=True,
            section='crawler_summary'
        )
    except Exception as e:
        logger.error(f"Failed to analyze website context with GPT: {e}")
        return {
            "industry": "General Business",
            "tone": "Professional, engaging",
            "topics": ["Company news", "Industry insights", "Product updates"],
            "brand_colors": ["#6366f1", "#4f46e5", "#f5f3ff", "#1f2937", "#a5b4fc"],
            "avg_read_time": "3.5m"
        }


def generate_suggested_ideas(website):
    """
    Uses GPT to generate 4 suggested content ideas (title, platform)
    based on the website's crawled topics, industry, and tone.
    """
    topics_str = ", ".join(website.topics) if website.topics else "General marketing, SEO, and business growth"
    prompt = f"""You are a content strategy generator for Cadence.
Analyze this website context:
- Name: {website.name}
- Industry: {website.industry or "Technology & Marketing"}
- Tone: {website.tone or "Professional"}
- Core Topics: {topics_str}

Generate 4 fresh, engaging, and trending content ideas for the year 2026.
Make sure they are highly specific to the business, and utilize modern trends (like ChatGPT, Perplexity, AI search, GEO, SGE, voice agents, etc. if relevant to their industry).

Return EXACTLY a JSON object with a single key "ideas" containing a list of 4 objects. Each object must have:
1. "title": A catchy headline/topic.
2. "platform": One of "blog", "linkedin", "instagram", "youtube" (choose platforms appropriate for the topics).

Return ONLY valid JSON. No code blocks or markdown."""

    try:
        data = call_llm(
            prompt,
            max_tokens=500,
            temperature=0.7,
            json_mode=True,
            website=website,
            section='idea_generation'
        )
        ideas = data.get("ideas", [])
        
        from content.models import ContentIdea
        created_ideas = []
        for item in ideas:
            title = item.get("title")
            platform = item.get("platform", "blog").lower()
            if platform not in ['blog', 'linkedin', 'instagram', 'facebook', 'youtube']:
                platform = 'blog'
            if title:
                import re
                title = re.sub(r'^\d+\s*\.\s*', '', title).strip()
                idea = ContentIdea.objects.create(
                    website=website,
                    title=title,
                    platform=platform,
                    status='pending'
                )
                created_ideas.append(idea)
        return created_ideas
    except Exception as e:
        logger.error(f"Failed to generate dynamic ideas: {e}")
        # Fallback to hardcoded ones based on industry
        from content.models import ContentIdea
        fallbacks = [
            ("How to Get Your Business Ready for Search Generative Experience (SGE) in 2026", "blog"),
            ("SEO vs GEO: Optimizing for AI Search Engines like Perplexity and ChatGPT", "linkedin"),
            ("Why Voice Search and AI Agents are Changing Digital Marketing", "blog"),
            ("5 AI tools every marketer needs to master this year", "instagram")
        ]
        created_ideas = []
        for title, plat in fallbacks:
            idea = ContentIdea.objects.create(
                website=website,
                title=title,
                platform=plat,
                status='pending'
            )
            created_ideas.append(idea)
        return created_ideas