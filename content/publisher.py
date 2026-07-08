"""
Sends approved content to make.com webhooks for social media posting.
Each platform has its own webhook URL configured in SocialConnection
or falling back to .env defaults.

Image Hosting Strategy:
  - Cover images are stored locally at /static/media/covers/*.png
  - For publishing (social/blog), a permanent public URL is required
  - We upload to imgbb.com (free, permanent) and cache the URL on draft.cover_image_public_url
  - This prevents repeated uploads and fixes the Instagram 9004 OAuthException
    caused by localhost URLs being sent to Make.com/Instagram API.
"""
import os
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

IMGBB_API_KEY = config('IMGBB_API_KEY', default='')


def upload_video_to_cloudinary(filepath) -> str:
    """
    Uploads a local video file to Cloudinary and returns the secure public CDN URL.
    """
    cloud_name = config('CLOUDINARY_CLOUD_NAME', default='')
    api_key = config('CLOUDINARY_API_KEY', default='')
    api_secret = config('CLOUDINARY_API_SECRET', default='')

    if not all([cloud_name, api_key, api_secret]):
        logger.info("Cloudinary credentials are not fully configured in .env. Skipping Cloudinary upload.")
        return ""

    import time
    import hashlib
    import requests

    timestamp = str(int(time.time()))
    raw_signature = f"timestamp={timestamp}{api_secret}"
    signature = hashlib.sha1(raw_signature.encode('utf-8')).hexdigest()

    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/video/upload"
    
    try:
        logger.info(f"Uploading video to Cloudinary: {filepath}")
        with open(filepath, 'rb') as f:
            files = {'file': f}
            data = {
                'api_key': api_key,
                'timestamp': timestamp,
                'signature': signature
            }
            response = requests.post(url, files=files, data=data, timeout=120)
            
        if response.status_code == 200:
            resp_json = response.json()
            public_url = resp_json.get('secure_url', '')
            logger.info(f"Cloudinary video upload successful: {public_url}")
            return public_url
        else:
            logger.error(f"Cloudinary video upload failed with HTTP {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Exception during Cloudinary video upload: {e}")
        
    return ""


def upload_cover_image_to_imgbb(draft) -> str:
    """
    Uploads the draft's cover image to imgbb.com and returns a permanent public URL.
    Caches the result in draft.cover_image_public_url to avoid repeated uploads.

    Returns:
        str: Public image URL, or empty string if upload fails / no image exists.
    """
    from django.conf import settings

    if not draft.cover_image:
        logger.warning(f"Draft {draft.id} has no cover_image path — skipping image upload.")
        return ""

    # Bypass imgbb for videos (or YouTube platform posts) since imgbb only hosts images
    is_video = draft.platform == 'youtube' or draft.cover_image.lower().endswith(('.mp4', '.webm', '.ogg', '.ogv', '.mov'))
    if is_video:
        rel_path = draft.cover_image.replace('/static/media/', '').replace('/static/', '')
        if 'covers/' in draft.cover_image:
            img_filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', 'covers', os.path.basename(rel_path))
        else:
            img_filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', os.path.basename(rel_path))
            
        if os.path.exists(img_filepath):
            cloudinary_url = upload_video_to_cloudinary(img_filepath)
            if cloudinary_url:
                # Cache on the draft so we don't re-upload
                draft.cover_image_public_url = cloudinary_url
                draft.save(update_fields=['cover_image_public_url'])
                return cloudinary_url

        domain = config('BACKEND_URL', default='http://localhost:8000')
        video_url = f"{domain.rstrip('/')}{draft.cover_image}"
        logger.info(f"Draft {draft.id} is a video/YouTube post. Direct video URL: {video_url}")
        return video_url

    # Return cached URL if already uploaded
    if draft.cover_image_public_url:
        logger.info(f"Using cached public image URL for draft {draft.id}: {draft.cover_image_public_url}")
        return draft.cover_image_public_url

    if not IMGBB_API_KEY:
        logger.error(
            "IMGBB_API_KEY is not configured in .env. "
            "Cannot upload cover image for public hosting. "
            "Add IMGBB_API_KEY=<your_key> to .env (get free key at https://api.imgbb.com/)"
        )
        return ""

    # Resolve local file path from the stored relative path
    rel_path = draft.cover_image.replace('/static/media/', '').replace('/static/', '')
    if 'covers/' in draft.cover_image:
        img_filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', 'covers', os.path.basename(rel_path))
    else:
        img_filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', os.path.basename(rel_path))

    if not os.path.exists(img_filepath):
        logger.error(f"Cover image file not found on disk: {img_filepath}")
        return ""

    try:
        logger.info(f"Uploading cover image to imgbb for draft {draft.id}: {img_filepath}")
        with open(img_filepath, 'rb') as img_file:
            import base64
            image_data = base64.b64encode(img_file.read()).decode('utf-8')

        response = requests.post(
            'https://api.imgbb.com/1/upload',
            data={
                'key': IMGBB_API_KEY,
                'image': image_data,
                'name': f"cadence_cover_{draft.id}",
            },
            timeout=30
        )

        if response.status_code == 200:
            resp_json = response.json()
            public_url = resp_json.get('data', {}).get('url', '')
            if public_url:
                # Cache on the draft so we don't re-upload
                draft.cover_image_public_url = public_url
                draft.save(update_fields=['cover_image_public_url'])
                logger.info(f"imgbb upload successful for draft {draft.id}: {public_url}")
                return public_url
            else:
                logger.error(f"imgbb returned 200 but no URL in response: {resp_json}")
        else:
            logger.error(f"imgbb upload failed with HTTP {response.status_code}: {response.text[:300]}")

    except Exception as e:
        logger.error(f"Exception during imgbb upload for draft {draft.id}: {e}")

    return ""


def send_to_make(scheduled_post: ScheduledPost) -> dict:
    """
    Sends content payload to make.com for social media platforms (Instagram, LinkedIn, etc.).
    DO NOT call this for blog platform — use publish_to_custom_blog() instead.

    Image URL strategy:
      1. Upload cover image to imgbb (permanent public URL)
      2. Send that URL in cover_image_url — Instagram/LinkedIn can fetch it directly
    """
    draft = scheduled_post.draft
    website = draft.website
    platform = draft.platform

    # Load platform-specific webhook from database first, fallback to .env
    from websites.models import SocialConnection
    webhook_url = ""
    try:
        conn = SocialConnection.objects.filter(website=website, platform=platform, is_active=True).first()
        if conn and conn.make_webhook_url:
            webhook_url = conn.make_webhook_url
    except Exception as e:
        logger.warning(f"Failed to lookup SocialConnection for website {website.id}: {e}")

    if not webhook_url:
        webhook_url = PLATFORM_WEBHOOK_DEFAULTS.get(platform, '')

    if not webhook_url:
        raise ValueError(f"No make.com webhook configured for platform: {platform}")

    # Upload cover image to imgbb for a permanent public URL
    public_image_url = upload_cover_image_to_imgbb(draft)
    if not public_image_url:
        logger.warning(
            f"No public image URL available for draft {draft.id} — "
            f"sending without image. Instagram will fail if image is required."
        )

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
        'cover_image_url': public_image_url,   # permanent imgbb URL (no localhost)
        'category': draft.category,
        'author_name': draft.author_name,
        'custom_date': draft.custom_date,

        # Schedule
        'scheduled_for': scheduled_post.scheduled_for.isoformat(),
    }

    # Add raw video base64 data to payload for direct upload (localtunnel bypass)
    # Only send base64 if not using Cloudinary (since Cloudinary gives a direct public URL)
    is_cloudinary = public_image_url and 'cloudinary.com' in public_image_url
    if platform == 'youtube' and draft.cover_image and not is_cloudinary:
        import base64
        from django.conf import settings
        rel_path = draft.cover_image.replace('/static/media/', '').replace('/static/', '')
        if 'covers/' in draft.cover_image:
            img_filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', 'covers', os.path.basename(rel_path))
        else:
            img_filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', os.path.basename(rel_path))
        if os.path.exists(img_filepath):
            try:
                logger.info(f"Reading and encoding video to base64 for YouTube upload: {img_filepath}")
                with open(img_filepath, 'rb') as f:
                    encoded_video = base64.b64encode(f.read()).decode('utf-8')
                payload['video_base64'] = encoded_video
                payload['video_filename'] = os.path.basename(img_filepath)
            except Exception as e:
                logger.error(f"Failed to read and encode video file: {e}")

    response = requests.post(
        webhook_url,
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    if response.status_code >= 400:
        logger.error(f"Make.com Webhook error response ({response.status_code}): {response.text}")
    response.raise_for_status()

    logger.info(f"Sent to make.com [{platform}]: {draft.title} → HTTP {response.status_code}")

    return {
        'status_code': response.status_code,
        'response_text': response.text[:500],
    }


def publish_to_custom_blog(draft, conn) -> dict:
    """
    Publishes blog draft directly to the website's configured custom blog endpoint.
    Decrypts the auth_payload credentials and sends the request.

    Image URL strategy:
      1. Upload cover image to imgbb (permanent public URL)
      2. Arogyra backend downloads image from this URL — not localhost
    """
    import json
    from websites.utils import decrypt_value
    from django.conf import settings

    url = conn.make_webhook_url
    auth_type = conn.auth_type

    auth_payload = {}
    if conn.auth_payload:
        try:
            auth_payload = json.loads(decrypt_value(conn.auth_payload))
        except Exception as e:
            logger.error(f"Failed to decrypt auth_payload for connection {conn.id}: {e}")

    # Build auth header
    headers = {}
    params = {}
    auth_credentials = None

    if auth_type == 'api_key':
        key_name = auth_payload.get('api_key_name', 'X-API-Key')
        key_value = auth_payload.get('api_key_value', '')
        headers[key_name] = key_value
    elif auth_type == 'api_key_query':
        key_name = auth_payload.get('api_key_name', 'api_key')
        key_value = auth_payload.get('api_key_value', '')
        params[key_name] = key_value
    elif auth_type == 'bearer_token':
        token = auth_payload.get('token_value', '')
        headers['Authorization'] = f"Bearer {token}"
    elif auth_type == 'basic_auth':
        username = auth_payload.get('username', '')
        password = auth_payload.get('password', '')
        from requests.auth import HTTPBasicAuth
        auth_credentials = HTTPBasicAuth(username, password)

    # Detect format preference from connection settings, fallback to vidhyacore.com domain matching
    is_form_data = auth_payload.get('payload_format') == 'form_data' or 'vidhyacore.com' in url.lower()
    clean_url = url

    if is_form_data:
        logger.info(f"Form-data target detected. Publishing via multipart/form-data to: {clean_url}")
        
        # Resolve local cover image path
        img_filepath = ""
        if draft.cover_image:
            rel_path = draft.cover_image.replace('/static/media/', '').replace('/static/', '')
            if 'covers/' in draft.cover_image:
                img_filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', 'covers', os.path.basename(rel_path))
            else:
                img_filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', os.path.basename(rel_path))

        # Build form-data payload fields
        tags_str = ", ".join(draft.tags) if isinstance(draft.tags, list) else (draft.tags or "")
        email_val = conn.website.contact_email or (conn.website.owner.email if conn.website.owner else "")
        
        # Safe truncation for meta SEO fields to avoid target DB constraints (usually VARCHAR(60) or VARCHAR(160))
        meta_title = draft.title
        if len(meta_title) > 60:
            meta_title = meta_title[:57] + "..."
            
        meta_desc = draft.meta_description or ""
        if len(meta_desc) > 160:
            meta_desc = meta_desc[:157] + "..."

        data_payload = {
            "title": draft.title,
            "content": draft.body,
            "description": draft.excerpt or draft.meta_description or draft.title,
            "tags": tags_str,
            "status": "PUBLISHED",
            "metaTitle": meta_title,
            "metaDescription": meta_desc,
            "metaKeywords": tags_str,
            "alt": draft.title,
            "canonical": conn.website.url,
            "email": email_val
        }

        # POST with file if it exists
        if img_filepath and os.path.exists(img_filepath):
            try:
                with open(img_filepath, 'rb') as f:
                    import mimetypes
                    mime_type, _ = mimetypes.guess_type(img_filepath)
                    if not mime_type:
                        mime_type = 'image/jpeg' if img_filepath.endswith(('.jpg', '.jpeg')) else 'image/png'
                    files = {'image': (os.path.basename(img_filepath), f, mime_type)}
                    response = requests.post(
                        clean_url,
                        data=data_payload,
                        files=files,
                        headers=headers,
                        params=params,
                        auth=auth_credentials if auth_type == 'basic_auth' else None,
                        timeout=60
                    )
            except Exception as e:
                logger.error(f"Failed to post to Vidhya Core with file: {e}")
                raise e
        else:
            response = requests.post(
                clean_url,
                data=data_payload,
                headers=headers,
                params=params,
                auth=auth_credentials if auth_type == 'basic_auth' else None,
                timeout=60
            )
    else:
        # Standard custom blog JSON implementation
        headers["Content-Type"] = "application/json"
        cover_image_url = upload_cover_image_to_imgbb(draft)
        if not cover_image_url:
            logger.warning(
                f"No public image URL available for blog draft {draft.id} — sending without cover_image_url."
            )
            cover_image_url = ""

        word_count = draft.word_count or len(draft.body.split())
        read_time_minutes = max(1, round(word_count / 200))
        read_time_display = f"{read_time_minutes} min read"

        json_payload = {
            "title": draft.title,
            "content": draft.body,
            "excerpt": draft.excerpt or "",
            "meta_description": draft.meta_description or "",
            "category": draft.category or "Technology",
            "read_time": read_time_display,
            "author_name": draft.author_name or "Cadence Publisher",
            "cover_image_url": cover_image_url,
            "tags": draft.tags or [],
            "flow": "all"
        }

        logger.info(f"Dispatching standard custom blog post to {url}...")
        response = requests.post(
            url,
            json=json_payload,
            headers=headers,
            params=params,
            auth=auth_credentials if auth_type == 'basic_auth' else None,
            timeout=30
        )

    if response.status_code >= 400:
        logger.error(f"Custom blog server error response ({response.status_code}): {response.text}")
    response.raise_for_status()

    try:
        result = response.json()
    except Exception:
        result = {"response_text": response.text[:500]}

    logger.info(f"Custom blog post completed successfully for draft {draft.id}")

    return {
        'status_code': response.status_code,
        'response': result,
        'url': result.get('url', url) if isinstance(result, dict) else url,
        'id': result.get('id', str(draft.id)) if isinstance(result, dict) else str(draft.id),
    }