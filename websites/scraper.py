"""
Scrapes a website to extract blog structure, tone, and style context.
Uses requests + BeautifulSoup for static sites.
Falls back to Playwright for JS-rendered sites.
"""
import re
import time
import logging
import datetime
from urllib.parse import urljoin, urlparse
from typing import Optional

import requests
from bs4 import BeautifulSoup
from django.utils.dateparse import parse_datetime
from dateutil.parser import parse as parse_date
from django.utils import timezone

logger = logging.getLogger(__name__)

SCRAPE_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36')
}

MAX_PAGES = 25   # Upgraded crawl limit: crawl up to 25 pages per website

CTA_KEYWORDS = {
    'buy', 'order', 'sign up', 'join', 'get', 'subscribe', 'download', 'contact',
    'start', 'register', 'try', 'learn more', 'explore', 'read more', 'click here',
    'shop', 'purchase', 'book', 'schedule', 'view'
}


def normalize_domain(netloc: str) -> str:
    """Strips leading 'www.' from a netloc string for domain comparison."""
    netloc = netloc.lower()
    if netloc.startswith('www.'):
        return netloc[4:]
    return netloc


def get_url_priority(url: str) -> int:
    """Heuristic priority: blog/article pages first, standard pages next, pagination last."""
    url_lower = url.lower()
    # Pagination patterns
    if 'page=' in url_lower or re.search(r'/page/\d+/?$', url_lower):
        return 3
    # Blog / Article heuristics (both with and without trailing slashes, including plurals)
    blog_indicators = [
        '/blog/', '/blog', '/blogs/', '/blogs',
        '/post/', '/post', '/posts/', '/posts',
        '/article/', '/article', '/articles/', '/articles',
        '/news/', '/news', '/stories/', '/stories'
    ]
    if any(k in url_lower for k in blog_indicators):
        return 1
    return 2


def parse_pub_date(date_str: str) -> Optional[datetime.datetime]:
    """Parse string representation of publication date into timezone-aware datetime."""
    if not date_str:
        return None
    try:
        dt = parse_datetime(date_str)
        if dt:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            return dt
        # dateutil parser fallback
        dt = parse_date(date_str)
        if dt:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            return dt
    except Exception:
        pass
    return None


def scrape_website(url: str) -> dict:
    """
    Entry point. Returns dict with:
    - pages: list of scraped page dictionaries
    - structure_summary: str (raw text summary for AI)
    """
    pages = []
    visited = set()
    to_visit = [url]
    base_domain = normalize_domain(urlparse(url).netloc)

    # Reusable browser context container to avoid launching browser repeatedly
    browser_ctx = {'playwright': None, 'browser': None}

    ABS_MAX_PAGES = 30 # Absolute limit to prevent runaways on very large sites
    
    try:
        while to_visit:
            # Sort queue so higher priority URLs (priority value 1) are popped first
            to_visit.sort(key=get_url_priority)
            
            # Check the next URL in queue
            next_url = to_visit[0]
            is_blog = get_url_priority(next_url) == 1
            
            # Stop if we hit the limit, unless the next page is a high-priority blog/article page
            if len(pages) >= MAX_PAGES:
                if not is_blog or len(pages) >= ABS_MAX_PAGES:
                    break
            
            current_url = to_visit.pop(0)
            
            if current_url in visited:
                continue
            visited.add(current_url)

            curr_limit = MAX_PAGES if (len(pages) < MAX_PAGES and not is_blog) else ABS_MAX_PAGES
            logger.info(f"Scraping page ({len(pages)+1}/{curr_limit}): {current_url}")
            page_data = _scrape_page(current_url, browser_ctx=browser_ctx)
            if not page_data:
                continue

            pages.append(page_data)

            # Discover internal links
            for link in page_data.get('internal_links', []):
                if link not in visited and normalize_domain(urlparse(link).netloc) == base_domain:
                    to_visit.append(link)
                    
            # Deduplicate to_visit
            to_visit = list(set(to_visit))
    finally:
        # Guarantee browser resource cleanup
        if browser_ctx['browser']:
            try:
                browser_ctx['browser'].close()
            except Exception:
                pass
        if browser_ctx['playwright']:
            try:
                browser_ctx['playwright'].stop()
            except Exception:
                pass

    return {
        'pages': pages,
        'structure_summary': _build_summary(pages),
    }


def _scrape_page(url: str, browser_ctx: Optional[dict] = None) -> Optional[dict]:
    """Scrapes a page using requests with backoff retry, falling back to Playwright if needed."""
    retries = 3
    backoff = 2
    resp_text = None
    
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=SCRAPE_HEADERS, timeout=15)
            resp.raise_for_status()
            resp_text = resp.text
            break
        except requests.RequestException as e:
            if attempt == retries - 1:
                logger.warning(f"Failed to scrape {url} via requests after {retries} attempts: {e}")
            else:
                sleep_time = backoff ** attempt
                logger.info(f"Retrying scrape of {url} in {sleep_time}s due to: {e}")
                time.sleep(sleep_time)

    if not resp_text:
        # Fall back to Playwright if static requests failed
        logger.info(f"Static request failed. Falling back to Playwright for {url}")
        return _scrape_page_playwright(url, browser_ctx)

    soup = BeautifulSoup(resp_text, 'html.parser')
    
    # Heuristic: if page is mostly empty / JS-heavy, try Playwright fallback
    body_text = soup.body.get_text(strip=True) if soup.body else ""
    if len(body_text) < 200:
        logger.info(f"Page body has minimal text ({len(body_text)} chars). Retrying with Playwright...")
        pw_result = _scrape_page_playwright(url, browser_ctx)
        if pw_result:
            return pw_result

    return _extract_from_soup(soup, url, resp_text)


def _scrape_page_playwright(url: str, browser_ctx: Optional[dict] = None) -> Optional[dict]:
    """Fallback for JS-rendered websites using Playwright."""
    browser = None
    own_instance = False
    p = None
    try:
        if browser_ctx:
            # Verify BOTH playwright instance and browser are healthy.
            # If either is missing (e.g. chromium.launch() failed last time),
            # tear down the stale playwright and restart both cleanly.
            pw = browser_ctx.get('playwright')
            br = browser_ctx.get('browser')
            if not pw or not br:
                # Cleanup any partial state
                if pw:
                    try:
                        pw.stop()
                    except Exception:
                        pass
                from playwright.sync_api import sync_playwright
                browser_ctx['playwright'] = sync_playwright().start()
                browser_ctx['browser'] = browser_ctx['playwright'].chromium.launch(headless=True)
            browser = browser_ctx['browser']
        else:
            from playwright.sync_api import sync_playwright
            p = sync_playwright().start()
            browser = p.chromium.launch(headless=True)
            own_instance = True

        page = browser.new_page()
        page.goto(url, timeout=25000, wait_until='domcontentloaded')
        page.wait_for_timeout(3000)
        html = page.content()
        page.close() # Close page context but keep browser alive

        if own_instance:
            browser.close()
            p.stop()
        
        soup = BeautifulSoup(html, 'html.parser')
        return _extract_from_soup(soup, url, html)
    except Exception as e:
        logger.error(f"Playwright fallback failed for {url}: {e}")
        if own_instance and browser:
            try:
                browser.close()
            except Exception:
                pass
        if own_instance and p:
            try:
                p.stop()
            except Exception:
                pass
        return None


def _score_content_nodes(parent):
    """Scores div/section/article elements based on text length, classes, and paragraph/link ratios."""
    candidates = parent.find_all(['div', 'section', 'article', 'main'])
    if not candidates:
        return parent
        
    best_node = parent
    best_score = -999999
    
    for node in candidates:
        text = node.get_text(strip=True)
        if len(text) < 100:
            continue
            
        score = 0
        paragraphs = node.find_all('p')
        score += len(paragraphs) * 10
        
        headings = node.find_all(['h2', 'h3', 'h4'])
        score += len(headings) * 5
        
        # Link density check
        words = text.split()
        if words:
            links = node.find_all('a')
            link_words = sum(len(a.get_text(strip=True).split()) for a in links)
            density = link_words / len(words)
            if density > 0.3:
                score -= 100
            score -= int(density * 50)
            
        # Class / ID matching
        node_class = " ".join(node.get('class', [])).lower()
        node_id = str(node.get('id', '')).lower()
        
        positive_patterns = {'content', 'article', 'post', 'body', 'entry-content', 'post-content', 'main-content', 'blog-post'}
        negative_patterns = {'sidebar', 'nav', 'footer', 'header', 'aside', 'menu', 'comments', 'share', 'social', 'widget', 'ads', 'banner'}
        
        if any(p in node_class or p in node_id for p in positive_patterns):
            score += 50
        if any(n in node_class or n in node_id for n in negative_patterns):
            score -= 100
            
        if score > best_score:
            best_score = score
            best_node = node
            
    return best_node


def _clean_html_structure(node) -> str:
    """Retains structural tags (headings, lists, blockquotes, paragraphs) and strips noise/interactive tags."""
    if not node:
        return ""
    clean_soup = BeautifulSoup(str(node), 'html.parser')
    allowed_tags = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li', 'blockquote', 'pre', 'code'}
    
    for tag in clean_soup.find_all(True):
        if tag.name not in allowed_tags:
            if tag.name in {'div', 'section', 'article', 'main', 'span', 'body', 'html'}:
                tag.unwrap()
            else:
                tag.decompose()
                
    return str(clean_soup).strip()


def _classify_page_type_helper(url: str, soup, author: str, pub_date) -> str:
    """Classifies a page into blog post, product page, about page, landing page, or other."""
    url_lower = url.lower()
    path = urlparse(url).path.lower()
    
    # 1. Product page heuristics
    if any(k in path for k in ['/product/', '/shop/', '/store/', '/item/']):
        return 'product page'
    if soup.find('meta', property='og:type', content='product') or soup.find(class_=re.compile(r'add-to-cart|buy-now|price', re.I)):
        return 'product page'
        
    # 2. About page heuristics
    if any(k in path for k in ['/about', '/team', '/who-we-are', '/our-story', '/careers']):
        return 'about page'
    if soup.title and any(k in soup.title.get_text().lower() for k in ['about us', 'about company', 'our team', 'who we are']):
        return 'about page'
        
    # 3. Blog post heuristics
    if any(k in path for k in ['/blog/', '/post/', '/article/', '/news/', '/stories/', '/posts/']) or re.search(r'/\d{4}/\d{2}/', path):
        return 'blog post'
    if soup.find('meta', property='og:type', content='article') or soup.find('meta', attrs={'name': 'og:type', 'content': 'article'}):
        return 'blog post'
    if soup.find('article') or (author and pub_date):
        return 'blog post'
    
    # JSON-LD Schema Type checks
    for schema in soup.find_all('script', type='application/ld+json'):
        try:
            import json
            data = json.loads(schema.string)
            schemas = data if isinstance(data, list) else [data]
            for s in schemas:
                s_type = str(s.get('@type', ''))
                if any(t in s_type for t in ['Article', 'BlogPosting', 'NewsArticle']):
                    return 'blog post'
                if s_type == 'Product':
                    return 'product page'
        except Exception:
            pass
            
    # 4. Landing page heuristics
    if any(k in path for k in ['/landing', '/welcome', '/promo', '/features']) or path in {'', '/'}:
        return 'landing page'
        
    return 'other'


def extract_colors_from_css(style_content: str) -> list:
    if not style_content:
        return []

    # Helper to convert rgb to hex
    def parse_rgb(match_groups):
        try:
            r, g, b = map(int, match_groups)
            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                return '#{:02x}{:02x}{:02x}'.format(r, g, b)
        except Exception:
            pass
        return None

    # Helper to convert hsl to hex
    def parse_hsl(match_groups):
        try:
            h = int(match_groups[0])
            s = int(match_groups[1])
            l = int(match_groups[2])
            if 0 <= h <= 360 and 0 <= s <= 100 and 0 <= l <= 100:
                import colorsys
                r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
                return '#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255))
        except Exception:
            pass
        return None

    # 1. Look for CSS variables representing primary/secondary/theme/accent colors
    var_colors = []
    # Match --var-name: #hex or rgb(...) or hsl(...)
    var_matches = re.findall(
        r'--(?:primary|secondary|accent|main|theme|color-primary|color-secondary|theme-meta-color)\s*:\s*([^;}\n]+)',
        style_content,
        re.I
    )
    for match in var_matches:
        color = match.strip().lower()
        # Try hex
        hex_match = re.search(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}', color)
        if hex_match:
            var_colors.append(hex_match.group(0))
            continue
        # Try rgb/rgba
        rgb_match = re.search(r'rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})', color)
        if rgb_match:
            hex_val = parse_rgb(rgb_match.groups())
            if hex_val:
                var_colors.append(hex_val)
                continue
        # Try hsl/hsla
        hsl_match = re.search(r'hsla?\(\s*(\d{1,3})[\s,]+(\d{1,3})%[\s,]+(\d{1,3})%', color)
        if hsl_match:
            hex_val = parse_hsl(hsl_match.groups())
            if hex_val:
                var_colors.append(hex_val)

    # 2. Extract and count frequency of all hex and rgb/hsl colors in stylesheets/HTML
    found_colors = []
    
    # Extract hex codes
    hex_codes = re.findall(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b', style_content)
    for h in hex_codes:
        h_lower = h.lower()
        if len(h_lower) == 4:
            h_lower = '#' + ''.join(c*2 for c in h_lower[1:])
        found_colors.append(h_lower)

    # Extract rgb/rgba values
    rgb_matches = re.findall(r'rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})', style_content, re.I)
    for groups in rgb_matches:
        hex_val = parse_rgb(groups)
        if hex_val:
            found_colors.append(hex_val)

    # Extract hsl/hsla values
    hsl_matches = re.findall(r'hsla?\(\s*(\d{1,3})[\s,]+(\d{1,3})%[\s,]+(\d{1,3})%', style_content, re.I)
    for groups in hsl_matches:
        hex_val = parse_hsl(groups)
        if hex_val:
            found_colors.append(hex_val)

    neutral_colors = {
        '#ffffff', '#000000', '#cccccc', '#eeeeee', '#333333', '#6c757d', 
        '#f8f9fa', '#e9ecef', '#dee2e6', '#ced4da', '#adb5bd', '#495057', 
        '#343a40', '#212529', '#1a1a1a', '#222222', '#f3f4f6', '#e5e7eb', 
        '#d1d5db', '#9ca3af', '#6b7280', '#4b5563', '#374151', '#1f2937', '#111827'
    }
    
    framework_colors = {
        '#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8', # Bootstrap defaults
        '#3b82f6', '#10b981', '#ef4444', '#f59e0b', '#06b6d4', # Tailwind defaults
        '#6366f1', '#4f46e5', '#f5f3ff', '#1f2937', '#a5b4fc',
        '#4a5568', '#2d3748', '#1a202c' # Tailwind grays
    }

    non_neutral_found = []
    neutral_found = []
    framework_found = []
    for col in found_colors:
        if col in neutral_colors:
            neutral_found.append(col)
        elif col in framework_colors:
            framework_found.append(col)
        else:
            non_neutral_found.append(col)

    # Count frequencies
    from collections import Counter
    common_non_neutral = [color for color, count in Counter(non_neutral_found).most_common(10)]
    common_neutral = [color for color, count in Counter(neutral_found).most_common(5)]
    common_framework = [color for color, count in Counter(framework_found).most_common(5)]

    # Combine prioritizing theme variables, then common non-neutrals, then common neutrals, then framework colors
    combined = []
    for c in var_colors:
        c_lower = c.lower()
        if len(c_lower) == 4:
            c_lower = '#' + ''.join(x*2 for x in c_lower[1:])
        if c_lower not in combined:
            combined.append(c_lower)
            
    for c in common_non_neutral:
        if c not in combined:
            combined.append(c)

    for c in common_neutral:
        if c not in combined:
            combined.append(c)

    for c in common_framework:
        if c not in combined:
            combined.append(c)

    return combined[:10]


def _extract_from_soup(soup: BeautifulSoup, url: str, raw_html: str) -> dict:
    """Extracts structured metadata, headings, main content, CTAs, comments, and page types."""
    title = soup.title.get_text().strip() if soup.title else ''
    meta_title = ""
    meta_desc = ""
    og_properties = {}
    pub_date = None
    author = ""
    categories_tags = []
    
    # Meta Titles
    meta_t = soup.find('meta', attrs={'property': 'og:title'}) or soup.find('meta', attrs={'name': 'twitter:title'})
    meta_title = meta_t['content'].strip() if meta_t and meta_t.get('content') else title
    
    # Meta Descriptions
    meta_d = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'}) or soup.find('meta', attrs={'name': 'twitter:description'})
    meta_desc = meta_d['content'].strip() if meta_d and meta_d.get('content') else ""
    
    # Open Graph properties
    for meta in soup.find_all('meta', property=True):
        prop = meta['property']
        if prop.startswith('og:') and meta.get('content'):
            og_properties[prop[3:]] = meta['content'].strip()
            
    # Publication Date
    time_tag = soup.find('time')
    pub_time_meta = (
        soup.find('meta', attrs={'property': 'article:published_time'}) or 
        soup.find('meta', itemprop='datePublished') or 
        soup.find('meta', attrs={'name': 'pubdate'})
    )
    date_str = ""
    if pub_time_meta and pub_time_meta.get('content'):
        date_str = pub_time_meta['content'].strip()
    elif time_tag and time_tag.get('datetime'):
        date_str = time_tag['datetime'].strip()
    elif time_tag:
        date_str = time_tag.get_text(strip=True)
        
    pub_date = parse_pub_date(date_str)
    
    # Author
    author_meta = (
        soup.find('meta', attrs={'name': 'author'}) or 
        soup.find('meta', attrs={'property': 'article:author'}) or 
        soup.find('meta', attrs={'name': 'twitter:creator'})
    )
    if author_meta and author_meta.get('content'):
        author = author_meta['content'].strip()
    else:
        author_el = soup.find(class_=re.compile(r'author|byline|creator|writer', re.I))
        if author_el:
            author = author_el.get_text(strip=True)
            author = re.sub(r'^by\s+', '', author, flags=re.I).strip()
            
    # Categories / keywords / tags
    keywords_meta = soup.find('meta', attrs={'name': 'keywords'}) or soup.find('meta', attrs={'property': 'article:tag'})
    if keywords_meta and keywords_meta.get('content'):
        categories_tags = [k.strip() for k in keywords_meta['content'].split(',') if k.strip()]
    else:
        section_meta = soup.find('meta', attrs={'property': 'article:section'})
        if section_meta and section_meta.get('content'):
            categories_tags.append(section_meta['content'].strip())

    # Main Content Area
    main_soup = soup.find('main') or soup.find('article') or soup.find('body') or soup
    
    # Try using readability if available and advanced is enabled
    from django.conf import settings
    enable_nlp = getattr(settings, 'ENABLE_ADVANCED_ANALYSIS', False)
    extracted = False
    main_content_html = ""
    image_source_soup = main_soup
    if enable_nlp:
        try:
            from readability import Document
            doc = Document(raw_html)
            summary_html = doc.summary()
            if summary_html:
                content_soup = BeautifulSoup(summary_html, 'html.parser')
                main_content_html = _clean_html_structure(content_soup)
                image_source_soup = BeautifulSoup(summary_html, 'html.parser')
                extracted = True
        except Exception as e:
            logger.warning(f"Readability-lxml extraction failed: {e}")
            
    if not extracted:
        scored_node = _score_content_nodes(main_soup)
        main_content_html = _clean_html_structure(scored_node)
        image_source_soup = scored_node

    # Clean text extracted from structured content
    temp_soup = BeautifulSoup(main_content_html, 'html.parser')
    raw_text = temp_soup.get_text(separator=' ', strip=True)
    raw_text = re.sub(r'\s+', ' ', raw_text)[:5000] # Limit database size
    
    # Classify Page Type
    page_type = _classify_page_type_helper(url, soup, author, pub_date)
    
    # Headings Structure
    headings = []
    for level in ['h1', 'h2', 'h3']:
        for h in temp_soup.find_all(level)[:10]:
            text_h = h.get_text(strip=True)
            if text_h:
                headings.append({'level': level, 'text': text_h})
                
    # Image Alt Texts
    image_alts = []
    for img in image_source_soup.find_all('img', alt=True):
        alt = img['alt'].strip()
        if alt:
            image_alts.append(alt)
            
    # Call to Actions (CTAs)
    ctas = []
    for element in main_soup.find_all(['a', 'button']):
        el_text = element.get_text(strip=True)
        if not el_text:
            continue
        el_class = " ".join(element.get('class', [])).lower()
        is_cta = False
        if any(c in el_class for c in ['btn', 'button', 'cta', 'signup', 'subscribe', 'register']):
            is_cta = True
        else:
            el_text_lower = el_text.lower()
            if any(el_text_lower.startswith(verb) or f" {verb} " in f" {el_text_lower} " for verb in CTA_KEYWORDS):
                is_cta = True
        if is_cta and len(el_text.split()) <= 8:
            ctas.append(el_text)
    ctas = list(set(ctas))[:10]
    
    # Comments (Up to 5)
    comments = []
    comment_containers = soup.find_all(class_=re.compile(r'comment|discussion|reply|thread', re.I))
    for container in comment_containers:
        for p in container.find_all('p'):
            comm_text = p.get_text(strip=True)
            if len(comm_text) > 15 and comm_text not in comments:
                comments.append(comm_text)
                if len(comments) >= 5:
                    break
        if len(comments) >= 5:
            break
            
    # Discover internal links
    internal_links = []
    base_domain = normalize_domain(urlparse(url).netloc)
    for a in soup.find_all('a', href=True):
        href = urljoin(url, a['href'])
        link_domain = normalize_domain(urlparse(href).netloc)
        if link_domain == base_domain:
            cleaned_href = href.split('?')[0].split('#')[0]
            internal_links.append(cleaned_href)

    # Discover fonts and text colors from style tags and linked stylesheets
    primary_font = ""
    heading_font = ""
    heading_color = ""
    text_color = ""
    
    # Discover theme colors from meta tags
    meta_theme_colors = []
    for meta_name in ['theme-color', 'msapplication-TileColor', 'msapplication-navbutton-color']:
        meta_tag = soup.find('meta', attrs={'name': meta_name})
        if meta_tag and meta_tag.get('content'):
            val = meta_tag['content'].strip()
            if val:
                meta_theme_colors.append(f"--theme-meta-color: {val};")

    style_tags = soup.find_all('style')
    style_content = "\n".join(meta_theme_colors) + "\n" + "\n".join([t.get_text() for t in style_tags])
    
    # Extract inline style attributes
    inline_styles = [el.get('style') for el in soup.find_all(style=True)]
    if inline_styles:
        style_content += "\n" + "\n".join(inline_styles)
        
    # Extract other color attributes (bgcolor, fill, stroke, color)
    other_colors = []
    for attr in ['bgcolor', 'fill', 'stroke', 'color']:
        other_colors.extend([el.get(attr) for el in soup.find_all(attrs={attr: True})])
    if other_colors:
        style_content += "\n" + "\n".join([c for c in other_colors if c])
    
    # Check linked stylesheets (internal only to avoid external requests blocking)
    for link in soup.find_all('link', rel='stylesheet', href=True):
        css_url = urljoin(url, link['href'])
        if normalize_domain(urlparse(css_url).netloc) == base_domain:
            try:
                css_resp = requests.get(css_url, headers=SCRAPE_HEADERS, timeout=5)
                if css_resp.status_code == 200:
                    style_content += "\n" + css_resp.text
            except Exception:
                pass
                
    # Regex matching on cumulative CSS styles
    if style_content:
        # 1. Primary font-family
        font_match = re.search(r'body\s*{[^}]*font-family:\s*([^;}]+)', style_content, re.I)
        if font_match:
            primary_font = font_match.group(1).strip().strip('"\'')
        else:
            font_match = re.search(r'font-family:\s*([^;}]+)', style_content, re.I)
            if font_match:
                primary_font = font_match.group(1).strip().strip('"\'')
                
        # 2. Heading font-family
        h_font_match = re.search(r'h[1-6]\s*{[^}]*font-family:\s*([^;}]+)', style_content, re.I)
        if h_font_match:
            heading_font = h_font_match.group(1).strip().strip('"\'')
            
        # 3. Body text color
        color_match = re.search(r'body\s*{[^}]*color:\s*([^;}]+)', style_content, re.I)
        if color_match:
            val = color_match.group(1).strip().lower()
            if val != 'transparent':
                text_color = color_match.group(1).strip()
            
        # 4. Heading text color
        h_color_match = re.search(r'h[1-6]\s*{[^}]*color:\s*([^;}]+)', style_content, re.I)
        if h_color_match:
            val = h_color_match.group(1).strip().lower()
            if val != 'transparent':
                heading_color = h_color_match.group(1).strip()
            
    # 1. Extract Logo
    logo_url = ""
    for img in soup.find_all('img'):
        alt = img.get('alt', '').lower()
        src = img.get('src', '')
        img_id = img.get('id', '')
        if isinstance(img_id, list):
            img_id = " ".join(img_id)
        img_id = img_id.lower()
        classes = " ".join(img.get('class', [])).lower()
        
        if src and ('logo' in alt or 'logo' in img_id or 'logo' in classes or 'logo' in src.lower()):
            logo_url = urljoin(url, src)
            break
            
    if not logo_url:
        og_img = soup.find('meta', property='og:image')
        if og_img and og_img.get('content'):
            logo_url = urljoin(url, og_img['content'])
            
    if not logo_url:
        for rel in ['icon', 'shortcut icon', 'apple-touch-icon']:
            fav = soup.find('link', rel=rel)
            if fav and fav.get('href'):
                logo_url = urljoin(url, fav['href'])
                break

    # 2. Extract emails
    text_content = soup.get_text()
    raw_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text_content)
    scraped_emails = []
    for email in raw_emails:
        email_lower = email.lower()
        if 'example.com' not in email_lower and 'placeholder' not in email_lower:
            scraped_emails.append(email)
    scraped_emails = list(dict.fromkeys(scraped_emails))

    # 3. Extract phone numbers
    raw_phones = re.findall(r'\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}', text_content)
    scraped_phones = []
    for phone in raw_phones:
        digits = re.sub(r'\D', '', phone)
        if 8 <= len(digits) <= 15:
            scraped_phones.append(phone.strip())
    scraped_phones = list(dict.fromkeys(scraped_phones))
            
    brand_colors = extract_colors_from_css(style_content)

    return {
        'url': url,
        'title': title,
        'meta_title': meta_title,
        'meta_description': meta_desc,
        'og_properties': og_properties,
        'publication_date': pub_date,
        'author': author,
        'categories_tags': categories_tags,
        'image_alts': image_alts,
        'page_type': page_type,
        'headings': headings,
        'text': raw_text,
        'word_count': len(raw_text.split()),
        'comments': comments,
        'ctas': ctas,
        'main_content': main_content_html,
        'internal_links': list(set(internal_links))[:30],
        'primary_font': primary_font,
        'heading_font': heading_font,
        'text_color': text_color,
        'heading_color': heading_color,
        'brand_colors': brand_colors,
        'logo_url': logo_url,
        'scraped_emails': scraped_emails,
        'scraped_phones': scraped_phones,
    }


def _build_summary(pages: list) -> str:
    """Builds a text summary of the website structure to use as AI context."""
    lines = []
    for p in pages:
        lines.append(f"PAGE: {p['title']} ({p['url']})")
        for h in p['headings'][:5]:
            lines.append(f"  {h['level'].upper()}: {h['text']}")
        lines.append(f"  EXCERPT: {p['text'][:300]}")
        lines.append("")
    return '\n'.join(lines)