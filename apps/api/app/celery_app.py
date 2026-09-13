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
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=60 * 60 * 24 * 7,
    # redbeat: Redis-backed dynamic scheduler for cron-triggered flows
    redbeat_redis_url=settings.redis_url,
    beat_scheduler="redbeat.schedulers:RedBeatScheduler",
    beat_max_loop_interval=5,
)
