from celery import Celery
from backend.config import REDIS_URL

celery_app = Celery(
    "pipeline",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
)
