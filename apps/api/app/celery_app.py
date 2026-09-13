from celery import Celery
from app.config import settings

celery_app = Celery(
    "nexus",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # don't ack until task completes (safe retry on worker crash)
    worker_prefetch_multiplier=1, # one task at a time per worker thread for long-running flows
    result_expires=60 * 60 * 24 * 7,  # keep results 7 days
)
