from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "gradetap",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


@celery_app.task(name="gradetap.ping")
def ping() -> str:
    return "pong"
