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
    
    # 1a. Fetch other published blog posts created within the platform
    platform_posts = ContentDraft.objects.filter(
        website=new_draft.website,
        platform='blog',
        status='published',
        is_deleted=False
    ).exclude(id=new_draft.id)
    
    for post in platform_posts:
        title = post.title.strip()
        tags = post.tags if isinstance(post.tags, list) else []
        post_url = f"{new_draft.website.url.rstrip('/')}/blog/{slugify(title)}"
        targets.append({
            'title': title,
            'tags': tags,
            'url': post_url
        })
        
    # 1b. Fetch crawled blog posts from the live site
    crawled_posts = ScrapeResult.objects.filter(
        website=new_draft.website,
        page_type='blog post'
    )
    
    for post in crawled_posts:
        title = post.page_title.strip()
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
        logger.info(f"No target posts (published drafts or crawled pages) found for website {new_draft.website.id}")
        return
        
    soup = BeautifulSoup(new_draft.body or '', 'html.parser')
    modified = False
    
    # 2. Match and link keywords
    for target in targets:
        title = target['title']
        tags = target['tags']
        post_url = target['url']
        
        # Target keywords: exact title, title parts (split by colons/dashes), then tags of length >= 3
        title_parts = [title] + [t.strip() for t in re.split(r'[:\-]', title) if t.strip() and t.strip() != title]
        keywords = title_parts + [tag for tag in tags if tag and len(tag) >= 3]
        
        linked = False
        for kw in keywords:
            if linked:
                break
                
            # Case-insensitive pattern matching whole words only
            pattern = re.compile(rf'\b({re.escape(kw)})\b', re.IGNORECASE)
            
            # Find all text nodes in the HTML document
            for text_node in soup.find_all(string=True):
                # Ignore text inside existing links, code blocks, or heading elements
                if text_node.parent and text_node.parent.name in ['a', 'code', 'pre', 'script', 'style', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    continue
                
                match = pattern.search(text_node)
                if match:
                    matched_text = match.group(0)
                    start, end = match.span()
                    
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
                    
                    linked = True
                    modified = True
                    logger.info(f"Injected link to {post_url} for keyword '{kw}' in draft {new_draft.id}")
                    break # Link only the first occurrence to avoid spamming links
                    
    # 3. Save the modified body back if changes occurred
    if modified:
        new_draft.body = str(soup)
        if new_draft.pk:
            new_draft.save(update_fields=['body'])
