from celery import Celery
from kombu import Queue

from dotenv import load_dotenv
import os
import logging
logger = logging.getLogger(__name__)
load_dotenv()


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")

if 'REDIS_URL' in os.environ:
    celery_app = celery(
        'tasks',
        broker=f"{os.getenv('REDIS_URL')}/0",
        broker_url=f"{os.getenv('REDIS_URL')}/0",
        backend=f"{os.getenv('REDIS_URL')}/1" 
        )
else:
    celery_app = celery(
        'tasks',
        broker=f"{os.getenv('REDIS_PROTOCOL')}://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REST_HOST')}:{os.getenv('REDIS_PORT')}/0",
        backend_url = f"{os.getenv('REDIS_PROTOCOL')}://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REST_HOST')}"
    )


