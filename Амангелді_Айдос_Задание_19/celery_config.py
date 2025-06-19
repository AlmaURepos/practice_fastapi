from celery import Celery
import os

app = Celery('app', broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'), backend=os.getenv('REDIS_URL', 'redis://redis:6379/0'))

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True
)

import tasks