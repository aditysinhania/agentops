from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from agentops_api.auth.dependencies import get_current_user
from agentops_api.db.session import get_db
from agentops_api.models.agent import Agent
from agentops_api.models.prompt import PromptVersion
from agentops_api.models.user import User
from agentops_api.schemas.entities import PromptCreate

router = APIRouter(prefix='/prompts', tags=['prompt versions'])


@router.get('')
def list_prompts(agent_id: str | None = None, page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(PromptVersion).where(PromptVersion.user_id == user.id)
    if agent_id:
        stmt = stmt.where(PromptVersion.agent_id == agent_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(PromptVersion.agent_id, PromptVersion.version.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {'items': items, 'total': total, 'page': page, 'page_size': page_size}


@router.post('', status_code=status.HTTP_201_CREATED)
def create_prompt(body: PromptCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.scalar(select(Agent.id).where(Agent.id == body.agent_id, Agent.user_id == user.id)):
        raise HTTPException(status_code=404, detail='Agent not found.')
    latest = db.scalar(select(func.max(PromptVersion.version)).where(PromptVersion.agent_id == body.agent_id)) or 0
    prompt = PromptVersion(user_id=user.id, agent_id=body.agent_id, version=latest + 1, label=body.label.strip(), content=body.content, notes=body.notes, regression_threshold=body.regression_threshold)
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt
