from celery import shared_task
from .publisher import send_to_make, send_to_arogyra
import logging
from logs.models import ActivityLog

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def generate_content_task(self, idea_id: int):
    try:
        from .generator import generate_for_idea
        draft_id = generate_for_idea(idea_id)
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
def regenerate_draft_task(self, draft_id: int):
    """Re-runs generation for an existing draft using its original idea."""
    try:
        from .models import ContentDraft
        from .generator import generate_for_idea
        
        draft = ContentDraft.objects.get(pk=draft_id)
        if draft.idea:
            new_draft_id = generate_for_idea(draft.idea_id)
            # Delete the old rejected draft
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
    from .publisher import send_to_make, send_to_arogyra
    
    now = timezone.now()
    due = ScheduledPost.objects.filter(
        scheduled_for__lte=now,
        is_published=False,
        draft__status='scheduled'
    ).select_related('draft__website')
    
    for sp in due:
        responses = {}
        arogyra_success = False
        make_success = False
        errors = []

        # 1. Send to Arogyra ONLY if platform is 'blog'
        if sp.draft.platform == 'blog':
            try:
                arogyra_result = send_to_arogyra(sp.draft)
                responses['arogyra'] = arogyra_result
                arogyra_success = True
                logger.info(f"Successfully sent to Arogyra: {sp.draft.title}")
            except Exception as e:
                error_msg = f"Arogyra publish failed: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        else:
            logger.info(f"Skipping Arogyra for non-blog post: {sp.draft.title} (platform: {sp.draft.platform})")

        # 2. Send to make.com (ALL platforms)
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
        if arogyra_success or make_success:
            sp.is_published = True
            sp.published_at = now
            sp.make_response = responses
            sp.save()
            sp.draft.status = 'published'
            sp.draft.save(update_fields=['status'])
            
            ActivityLog.objects.create(
                actor=None, actor_name='Scheduler',
                action='content_published',
                target_description=f"{sp.draft.title} → Arogyra: {arogyra_success}, make.com: {make_success}"
            )
            logger.info(f"Published: {sp.draft.title} (Arogyra: {arogyra_success}, make.com: {make_success})")
        else:
            logger.error(f"Both publishers failed for {sp.draft.title}: {errors}")