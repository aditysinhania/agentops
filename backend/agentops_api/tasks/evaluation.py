from agentops_api.services.run_eval import mark_evaluation_failed, run_evaluation
from agentops_api.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10, name='agentops.evaluate')
def evaluate_task(self, run_id: str):
    try:
        run_evaluation(run_id, raise_on_error=True)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            mark_evaluation_failed(run_id, str(exc))
            return {'status': 'failed', 'run_id': run_id}
        raise self.retry(exc=exc)
    return {'status': 'completed', 'run_id': run_id}
