from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "anb_workers",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['app.workers.video_processor']
)

# Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'app.workers.video_processor.process_video_task': 'video_queue'
    }
)