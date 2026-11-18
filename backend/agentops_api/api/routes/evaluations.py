from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from agentops_api.auth.dependencies import get_current_user
from agentops_api.config import settings
from agentops_api.db.session import get_db
from agentops_api.db.repositories import find_owned_evaluation
from agentops_api.models.agent import Agent
from agentops_api.models.dataset import Dataset
from agentops_api.models.evaluation import EvalRun
from agentops_api.models.prompt import PromptVersion
from agentops_api.models.user import User
from agentops_api.schemas.entities import EvalCreate
from agentops_api.services.run_eval import run_evaluation

router = APIRouter(prefix='/evaluations', tags=['evaluations'])


def owned_run(db: Session, user_id: str, run_id: str) -> EvalRun:
    run = find_owned_evaluation(db, user_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='Evaluation run not found.')
    return run


@router.get('')
def list_runs(page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(EvalRun).where(EvalRun.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(EvalRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {'items': rows, 'total': total, 'page': page, 'page_size': page_size}


@router.post('', status_code=status.HTTP_202_ACCEPTED)
def create_run(body: EvalCreate, background_tasks: BackgroundTasks, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = db.scalar(select(Dataset).where(Dataset.id == body.dataset_id, Dataset.user_id == user.id))
    if not dataset:
        raise HTTPException(status_code=404, detail='Dataset not found.')
    if body.agent_id and not db.scalar(select(Agent.id).where(Agent.id == body.agent_id, Agent.user_id == user.id)):
        raise HTTPException(status_code=404, detail='Agent not found.')
    if body.prompt_version_id and not db.scalar(select(PromptVersion.id).where(PromptVersion.id == body.prompt_version_id, PromptVersion.user_id == user.id)):
        raise HTTPException(status_code=404, detail='Prompt version not found.')
    if body.evaluator == 'llm_judge' and not (settings.groq_api_key or settings.gemini_api_key):
        raise HTTPException(status_code=400, detail='LLM-as-a-judge requires GROQ_API_KEY or GEMINI_API_KEY. Rule-based evaluations do not require a provider key.')
    if settings.queue_mode.lower() == 'celery':
        if not settings.redis_url:
            raise HTTPException(status_code=503, detail='Celery queue mode is selected but REDIS_URL is unavailable.')
        try:
            from redis import Redis
            Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2).ping()
        except Exception:
            raise HTTPException(status_code=503, detail='The configured Redis queue is unavailable; the evaluation was not created.') from None
    run = EvalRun(user_id=user.id, dataset_id=dataset.id, agent_id=body.agent_id, prompt_version_id=body.prompt_version_id, name=body.name.strip(), total_cases=0, metrics={'selected': body.metrics, 'evaluator': body.evaluator})
    db.add(run)
    db.commit()
    db.refresh(run)
    if settings.queue_mode.lower() == 'celery':
        from agentops_api.tasks.evaluation import evaluate_task
        evaluate_task.delay(run.id)
    else:
        background_tasks.add_task(run_evaluation, run.id)
    return run


@router.get('/{run_id}')
def get_run(run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return owned_run(db, user.id, run_id)
