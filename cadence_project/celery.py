import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')

app = Celery('cadence_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    # Check for scheduled posts every minute
    'publish-scheduled-posts': {
        'task': 'content.tasks.publish_scheduled_posts',
        'schedule': 60.0,   # every 60 seconds
    },
}