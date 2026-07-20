release: python manage.py migrate --noinput
web: gunicorn cadence_project.wsgi --log-file -
worker: celery -A cadence_project worker -l info
beat: celery -A cadence_project beat -l info
