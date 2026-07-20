from celery import shared_task
from .publisher import send_to_make
import logging
from logs.models import ActivityLog

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def generate_content_task(self, idea_id: int, include_infographics: bool = True, include_cta: bool = True):
    try:
        from .generator import generate_for_idea
        draft_id = generate_for_idea(idea_id, include_infographics=include_infographics, include_cta=include_cta)
        ActivityLog.objects.create(
            actor=None, actor_name='AI Engine',
            action='content_generated',
            target_description=f"Draft #{draft_id} generated"
        )
        return {'draft_id': draft_id}
    except Exception as exc:
        logger.error(f"generate_content_task failed for idea {idea_id}: {exc}")
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=2)
def regenerate_draft_task(self, draft_id: int, regenerate_type: str = 'all'):
    """Re-runs generation for an existing draft using its original idea."""
    try:
        from .models import ContentDraft
        from .generator import generate_for_idea
        
        draft = ContentDraft.objects.select_related('idea', 'website').get(pk=draft_id)
        new_draft_id = draft_id
        
        if regenerate_type == 'image':
            from .generator import generate_svg_cover_via_gpt
            from django.conf import settings
            import os
            import uuid
            
            category_name = draft.category or 'General'
            svg_code, png_filename = generate_svg_cover_via_gpt(
                draft.title, 
                category_name, 
                excerpt=draft.excerpt or '', 
                website=draft.website
            )
            
            if png_filename:
                media_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media')
                filepath = os.path.join(media_dir, png_filename)
                public_url = ""
                try:
                    from .generator import _upload_bytes_to_imgbb
                    with open(filepath, 'rb') as img_f:
                        public_url = _upload_bytes_to_imgbb(img_f.read(), png_filename)
                except Exception as upload_err:
                    logger.warning(f"Failed to upload regenerated cover to ImgBB: {upload_err}")
                draft.cover_image = public_url if public_url else f"/static/media/{png_filename}"
            elif svg_code:
                import base64
                svg_base64 = base64.b64encode(svg_code.encode('utf-8')).decode('utf-8')
                draft.cover_image = f"data:image/svg+xml;base64,{svg_base64}"
            
            draft.cover_image_public_url = draft.cover_image if draft.cover_image.startswith('http') else ""
            draft.save(update_fields=['cover_image', 'cover_image_public_url'])
            new_draft_id = draft.id
        elif regenerate_type == 'content':
            if draft.idea:
                new_draft_id = generate_for_idea(
                    draft.idea_id, generate_image=False,
                    include_infographics=draft.include_infographics,
                    include_cta=draft.include_cta
                )
                new_draft = ContentDraft.objects.get(pk=new_draft_id)
                new_draft.cover_image = draft.cover_image
                new_draft.cover_image_public_url = draft.cover_image_public_url
                new_draft.save(update_fields=['cover_image', 'cover_image_public_url'])
                draft.delete()
        else:
            if draft.idea:
                new_draft_id = generate_for_idea(
                    draft.idea_id,
                    include_infographics=draft.include_infographics,
                    include_cta=draft.include_cta
                )
                draft.delete()
                
        return {'new_draft_id': new_draft_id}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


# @shared_task
# def publish_scheduled_posts():
#     """
#     Runs every minute via Celery Beat.
#     Finds approved+scheduled posts due to publish and fires make.com webhook.
#     """
#     from django.utils import timezone
#     from .models import ScheduledPost
#     from .publisher import send_to_make
    
#     now = timezone.now()
#     due = ScheduledPost.objects.filter(
#         scheduled_for__lte=now,
#         is_published=False,
#         draft__status='scheduled'
#     ).select_related('draft__website')
    
#     for sp in due:
#         try:
#             result = send_to_make(sp)
#             sp.is_published = True
#             sp.published_at = now
#             sp.make_response = result
#             sp.save()
#             sp.draft.status = 'published'
#             sp.draft.save(update_fields=['status'])
#             ActivityLog.objects.create(
#                 actor=None, actor_name='Scheduler',
#                 action='content_published',
#                 target_description=f"{sp.draft.title} → {sp.draft.platform}"
#             )
#             logger.info(f"Published: {sp.draft.title}")
#         except Exception as e:
#             logger.error(f"Failed to publish scheduled post {sp.id}: {e}")   




@shared_task
def publish_scheduled_posts():
    """
    Runs every minute via Celery Beat.
    Finds approved+scheduled posts due to publish.
    - Sends BLOG posts to Arogyra.
    - Sends ALL posts to make.com.
    """
    from django.utils import timezone
    from .models import ScheduledPost
    from .publisher import send_to_make
    
    now = timezone.now()
    due = ScheduledPost.objects.filter(
        scheduled_for__lte=now,
        is_published=False,
        draft__status='scheduled'
    ).select_related('draft__website')
    
    for sp in due:
        responses = {}
        blog_success = False
        make_success = False
        errors = []

        # 1. Send to Custom Blog ONLY if platform is 'blog'
        if sp.draft.platform == 'blog':
            try:
                from websites.models import SocialConnection
                from .publisher import publish_to_custom_blog
                
                # Check for active custom blog connection
                custom_conn = SocialConnection.objects.filter(
                    website=sp.draft.website,
                    platform='blog',
                    is_active=True
                ).first()
                
                if custom_conn and custom_conn.make_webhook_url:
                    blog_result = publish_to_custom_blog(sp.draft, custom_conn)
                    responses['blog'] = blog_result
                    blog_success = True
                    logger.info(f"Successfully published to custom blog endpoint: {sp.draft.title}")
                else:
                    raise ValueError(f"No custom blog endpoint configured in database for website: {sp.draft.website.name}")
            except Exception as e:
                error_msg = f"Blog publish failed: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        else:
            logger.info(f"Skipping blog publishing for non-blog post: {sp.draft.title} (platform: {sp.draft.platform})")

        # 2. Send to make.com (ONLY for social platforms)
        if sp.draft.platform != 'blog':
            try:
                make_result = send_to_make(sp)
                responses['make'] = make_result
                make_success = True
                logger.info(f"Successfully sent to make.com: {sp.draft.title}")
            except Exception as e:
                error_msg = f"make.com publish failed: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # If at least one succeeded, mark as published
        if blog_success or make_success:
            sp.is_published = True
            sp.published_at = now
            sp.make_response = responses
            sp.save()
            sp.draft.status = 'published'
            sp.draft.save(update_fields=['status'])
            
            ActivityLog.objects.create(
                actor=None, actor_name='Scheduler',
                action='content_published',
                target_description=f"{sp.draft.title} → Blog: {blog_success}, make.com: {make_success}"
            )
            logger.info(f"Published: {sp.draft.title} (Blog: {blog_success}, make.com: {make_success})")
        else:
            logger.error(f"Publishing failed for {sp.draft.title}: {errors}")


@shared_task
def republish_published_post_task(draft_id: int):
    """
    Called when a draft that was already published is edited.
    Triggers the custom blog or social publishing logic to perform an update on the live site.
    """
    from .models import ContentDraft
    from websites.models import SocialConnection
    from .publisher import publish_to_custom_blog
    
    try:
        draft = ContentDraft.objects.get(pk=draft_id)
    except ContentDraft.DoesNotExist:
        logger.warning(f"Draft {draft_id} does not exist. Skipping republish.")
        return False
        
    if draft.status != 'published':
        logger.warning(f"Draft {draft_id} is not in published status. Skipping republish.")
        return False
        
    logger.info(f"Republishing updated published post: {draft.title} (ID: {draft.id})")
    
    if draft.platform == 'blog':
        try:
            custom_conn = SocialConnection.objects.filter(
                website=draft.website,
                platform='blog',
                is_active=True
            ).first()
            if custom_conn and custom_conn.make_webhook_url:
                from .publisher import republish_to_custom_blog
                result = republish_to_custom_blog(draft, custom_conn)
                logger.info(
                    f"Live blog republish complete for '{draft.title}' "
                    f"via {result.get('method', 'unknown')} → {result.get('url', '')}"
                )
                return True
            else:
                logger.warning("No custom blog connection configured, skipping live republish.")
        except Exception as e:
            logger.error(f"Live blog update failed: {e}")
            raise e
    return False