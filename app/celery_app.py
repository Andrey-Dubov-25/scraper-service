import os
from celery import Celery

BROKER = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

app = Celery(
    'scraper_service',
    broker=BROKER,
    backend=BACKEND,
    include=['app.tasks']
)

app.conf.task_track_started = True

app.conf.task_default_queue = 'celery'