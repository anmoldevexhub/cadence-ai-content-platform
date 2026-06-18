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


def send_to_make(scheduled_post: ScheduledPost) -> dict:
    """
    Sends content payload to make.com.
    make.com scenario then handles the actual posting to the platform.
    """
    draft = scheduled_post.draft
    website = draft.website
    platform = draft.platform
    
    # Find platform-specific webhook (from SocialConnection first, then .env)
    try:
        conn = website.social_connections.get(platform=platform, is_active=True)
        webhook_url = conn.make_webhook_url or PLATFORM_WEBHOOK_DEFAULTS.get(platform, '')
    except Exception:
        webhook_url = PLATFORM_WEBHOOK_DEFAULTS.get(platform, '')
    
    if not webhook_url:
        raise ValueError(f"No make.com webhook configured for platform: {platform}")
    
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