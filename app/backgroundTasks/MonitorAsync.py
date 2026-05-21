from celery import Celery
from kombu import Queue

from dotenv import load_dotenv
import os
import logging
logger = logging.getLogger(__name__)
load_dotenv()


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")

if 'REDIS_URL' in os.environ:
    celery_app = Celery(
        'tasks',
        broker=f"{os.getenv('REDIS_URL')}/0",
        broker_url=f"{os.getenv('REDIS_URL')}/0",
        backend=f"{os.getenv('REDIS_URL')}/1" 
        )
else:
    celery_app = Celery(
        'tasks',
        broker=f"{os.getenv('REDIS_PROTOCOL')}://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/0",
        backend_url = f"{os.getenv('REDIS_PROTOCOL')}://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/0",
        backend = f"{os.getenv('REDIS_PROTOCOL')}://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/0"
    )

celery_app.conf.update(
    broker_use_ssl = None,
    redis_backend_user_ssl = None,
    task_track_started= True,
    broker_connection_retry_on_startup = True,
    task_serializer= "json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_queues=[
        Queue("ip_app_queue", routing_key="ip_app.#"),
    ],
    task_default_queue="ip_app_queue",
    task_default_exchange="ip_app",
    task_default_routing_key="ip_app.default",
    imports=[
        "app.templates.send_template_mail"
    ],
)


class MonitorAsync:
    @classmethod
    def deferred(cls, function, *args):
        task_name = getattr(function, 'name', f"{function.__module__}.{function.__name__}")
        logger.info(f"Preparing to send task:{task_name} with args: {args}")
        if task_name not in celery_app.tasks:
            logger.error(f"Task '{task_name}' is not registered with Celery. Registered tasks: {list(celery_app.tasks.keys())}")
            raise ValueError(f"Task '{task_name}' is not registered with Celery. Registered tasks: {list(celery_app.tasks.keys())}")
        task = celery_app.send_task(task_name, args=args)
        logger.info(f"Task Sent: {task}")
        return task
    



