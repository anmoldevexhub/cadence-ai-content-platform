import re
import logging
from bs4 import BeautifulSoup
from django.utils.text import slugify

logger = logging.getLogger(__name__)

def inject_internal_links(new_draft):
    """
    Scans the generated blog post body and automatically inserts <a> links
    referencing other published posts (from ContentDraft) or crawled posts (from ScrapeResult)
    on the same website.
    """
    if new_draft.platform != 'blog':
        return
    
    from content.models import ContentDraft
    from websites.models import ScrapeResult
    
    targets = []
    
    # 1. Fetch crawled pages from the live site (only crawled data)
    crawled_posts = ScrapeResult.objects.filter(website=new_draft.website)
    
    for post in crawled_posts:
        title = post.page_title.strip()
        if not title:
            continue
        tags = post.categories_tags if isinstance(post.categories_tags, list) else []
        post_url = post.page_url
        
        # Deduplicate: Avoid adding if the URL or title is already a target
        if not any(t['url'].rstrip('/') == post_url.rstrip('/') or t['title'].lower() == title.lower() for t in targets):
            targets.append({
                'title': title,
                'tags': tags,
                'url': post_url
            })
            
    if not targets:
        logger.info(f"No target crawled pages found for website {new_draft.website.id}")
        return
        
    soup = BeautifulSoup(new_draft.body or '', 'html.parser')
    modified = False
    
    used_anchors = set()
    
    # 2. Match and link keywords
    for target in targets:
        title = target['title']
        tags = target['tags']
        post_url = target['url']
        
        # Target keywords: exact title, title parts, and tags
        # Split by punctuation (excluding hyphens) and common transition words/prepositions to extract sub-phrases
        delimiters = r'[:\?|,\.]|\b(?:help|achieve|for|in|on|with|by|and|to|is|are|the|how|why|about)\b'
        parts = re.split(delimiters, title, flags=re.IGNORECASE)
        
        # Clean title parts and strip leading stop words
        stop_words = {'how', 'why', 'the', 'a', 'an', 'what', 'is', 'are', 'about', 'to', 'for', 'in', 'on', 'with', 'by'}
        extracted_parts = []
        for p in parts:
            p_clean = p.strip()
            # Loop to strip leading stop words
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
        raw_keywords = title_parts + [tag for tag in tags if tag]
        
        # Filter keywords: must be multi-word phrases (>= 2 words) or specific terms (>= 6 chars and not generic)
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
        
        # Prevent duplicate links to the same target URL in the entire article
        existing_links = [a.get('href') for a in soup.find_all('a', href=True)]
        if any(post_url.rstrip('/') == url.rstrip('/') for url in existing_links):
            continue

        linked = False
        for kw in keywords:
            if linked:
                break
                
            # Prevent duplicate or overlapping links in the same article
            if any(kw.lower() in anchor or anchor in kw.lower() for anchor in used_anchors):
                continue
                
            # Case-insensitive pattern matching whole words only
            pattern = re.compile(rf'\b({re.escape(kw)})\b', re.IGNORECASE)
            
            # Find all text nodes in the HTML document
            for text_node in soup.find_all(string=True):
                # Ignore text inside existing links, code blocks, or heading elements
                if text_node.parent and text_node.parent.name in ['a', 'code', 'pre', 'script', 'style', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    continue
                
                match = pattern.search(text_node)
                if match:
                    start, end = match.span()
                    
                    # Prevent matching inside hyphenated compound words (e.g. Goal-based agents)
                    has_leading_hyphen = start > 0 and text_node[start - 1] == '-'
                    has_trailing_hyphen = end < len(text_node) and text_node[end] == '-'
                    if has_leading_hyphen or has_trailing_hyphen:
                        continue
                        
                    matched_text = match.group(0)
                    
                    # Split the text around the match
                    prev_text = text_node[:start]
                    post_text = text_node[end:]
                    
                    # Create the new link element
                    new_link = soup.new_tag('a', href=post_url, target="_blank")
                    new_link.string = matched_text
                    
                    # Reconstruct the HTML text node tree
                    if post_text:
                        text_node.insert_after(soup.new_string(post_text))
                    text_node.insert_after(new_link)
                    if prev_text:
                        text_node.replace_with(soup.new_string(prev_text))
                    else:
                        text_node.extract()
                    
                    used_anchors.add(matched_text.lower())
                    linked = True
                    modified = True
                    logger.info(f"Injected link to {post_url} for keyword '{kw}' in draft {new_draft.id}")
                    break # Link only the first occurrence to avoid spamming links
                    
    # 3. Save the modified body back if changes occurred
    if modified:
        new_draft.body = str(soup)
        if new_draft.pk:
            new_draft.save(update_fields=['body'])
