"""
Sends approved content to make.com webhooks for social media posting.
Each platform has its own webhook URL configured in SocialConnection 
or falling back to .env defaults.
"""
import requests
import logging
from decouple import config
from .models import ScheduledPost

logger = logging.getLogger(__name__)

PLATFORM_WEBHOOK_DEFAULTS = {
    'blog':       config('MAKE_BLOG_WEBHOOK', default=''),
    'instagram':  config('MAKE_INSTAGRAM_WEBHOOK', default=''),
    'linkedin':   config('MAKE_LINKEDIN_WEBHOOK', default=''),
    'facebook':   config('MAKE_FACEBOOK_WEBHOOK', default=''),
    'youtube':    config('MAKE_YOUTUBE_WEBHOOK', default=''),
}


def get_absolute_cover_url(cover_image: str) -> str:
    if not cover_image:
        return ""
    if cover_image.startswith('http://') or cover_image.startswith('https://'):
        return cover_image
    backend_url = config('BACKEND_URL', default='http://localhost:8000')
    return f"{backend_url.rstrip('/')}/{cover_image.lstrip('/')}"


def send_to_make(scheduled_post: ScheduledPost) -> dict:
    """
    Sends content payload to make.com.
    make.com scenario then handles the actual posting to the platform.
    """
    import base64
    import os
    from django.conf import settings

    draft = scheduled_post.draft
    website = draft.website
    platform = draft.platform
    
    # Load platform-specific webhook directly from .env configuration
    webhook_url = PLATFORM_WEBHOOK_DEFAULTS.get(platform, '')
    
    if not webhook_url:
        raise ValueError(f"No make.com webhook configured for platform: {platform}")
    
    # Load and encode cover image as base64 and upload to tmpfiles.org for public URL
    cover_image_base64 = ""
    cover_image_filename = ""
    cover_image_path = draft.cover_image
    public_hosted_url = ""
    if cover_image_path:
        rel_path = cover_image_path.replace('/static/media/', '').replace('/static/', '')
        img_filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', os.path.basename(rel_path))
        if os.path.exists(img_filepath):
            # 1. Base64 encode
            try:
                cover_image_filename = os.path.basename(img_filepath)
                with open(img_filepath, 'rb') as img_f:
                    cover_image_base64 = base64.b64encode(img_f.read()).decode('utf-8')
                logger.info(f"Successfully encoded cover image {cover_image_filename} to base64.")
            except Exception as b64_err:
                logger.warning(f"Failed to encode cover image to base64: {b64_err}")
            
            # 2. Upload to tmpfiles.org for direct public URL
            try:
                logger.info(f"Uploading cover image to tmpfiles.org for direct public URL...")
                with open(img_filepath, 'rb') as img_f:
                    up_resp = requests.post(
                        'https://tmpfiles.org/api/v1/upload',
                        files={'file': img_f},
                        timeout=20
                    )
                if up_resp.status_code == 200:
                    up_data = up_resp.json()
                    raw_url = up_data.get('data', {}).get('url', '')
                    if raw_url:
                        public_hosted_url = raw_url.replace('https://tmpfiles.org/', 'https://tmpfiles.org/dl/')
                        logger.info(f"Successfully uploaded cover image to tmpfiles.org: {public_hosted_url}")
            except Exception as up_err:
                logger.warning(f"Failed to upload cover image to tmpfiles.org: {up_err}")
    
    payload = {
        # Website info
        'website_name': website.name,
        'website_domain': website.domain,
        'website_url': website.url,
        
        # Content
        'platform': platform,
        'content_id': draft.id,
        'title': draft.title,
        'body': draft.body,
        'excerpt': draft.excerpt,
        'meta_description': draft.meta_description,
        'tags': draft.tags,
        'word_count': draft.word_count,
        'cover_image': draft.cover_image,
        'cover_image_url': public_hosted_url or get_absolute_cover_url(draft.cover_image),
        'cover_image_filename': cover_image_filename,
        'cover_image_base64': cover_image_base64,
        'category': draft.category,
        'author_name': draft.author_name,
        'custom_date': draft.custom_date,
        
        # Schedule
        'scheduled_for': scheduled_post.scheduled_for.isoformat(),
    }
    
    response = requests.post(
        webhook_url,
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    response.raise_for_status()
    
    logger.info(f"Sent to make.com [{platform}]: {draft.title} → HTTP {response.status_code}")
    
    return {
        'status_code': response.status_code,
        'response_text': response.text[:500],
    }






def send_to_arogyra(draft) -> dict:
    """
    Sends blog content directly to Arogyra's blog creation API.
    """
    import requests
    from decouple import config
    from django.conf import settings

    # Arogyra API endpoint
    api_url = config('AROGYRA_API_URL', default='http://localhost:8000/api/blogs/create/')
    
    # Arogyra API Key
    api_key = config('AROGYRA_API_KEY', default='arogyra-default-blog-post-key-2026')
    
    # Calculate read time
    word_count = draft.word_count or len(draft.body.split())
    read_time_minutes = max(1, round(word_count / 200))
    read_time_display = f"{read_time_minutes} min read"
    
    # Get cover image URL with safe fallback for BASE_URL
    cover_image_url = ""
    if draft.cover_image:
        if draft.cover_image.startswith('http://') or draft.cover_image.startswith('https://'):
            cover_image_url = draft.cover_image
        else:
            # Safely get BASE_URL with fallback
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8006')
            cover_image_url = f"{base_url}{draft.cover_image}"
    
    # Build payload
    payload = {
        "title": draft.title,
        "content": draft.body,
        "category": draft.category or "Technology",
        "read_time": read_time_display,
        "author_name": draft.author_name or "Devex Hub",
        "cover_image_url": cover_image_url,
        "flow": "all"
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Blog posted to Arogyra: {draft.title} → ID: {result.get('id')}")
        return {
            'status_code': response.status_code,
            'response': result,
            'url': result.get('url', ''),
            'id': result.get('id', ''),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to post to Arogyra: {e}")
        raise