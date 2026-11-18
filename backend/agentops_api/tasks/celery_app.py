from celery import Celery
from agentops_api.config import settings

celery_app = Celery('agentops', broker=settings.redis_url or 'redis://localhost:6379/0', backend=settings.redis_url or 'redis://localhost:6379/1', include=['agentops_api.tasks.evaluation'])
celery_app.conf.update(
    task_serializer='json', result_serializer='json', accept_content=['json'], timezone='UTC', enable_utc=True,
    task_acks_late=True, task_reject_on_worker_lost=True, worker_prefetch_multiplier=1,
    task_soft_time_limit=300, task_time_limit=360,
)
