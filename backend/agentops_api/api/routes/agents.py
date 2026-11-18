from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from agentops_api.auth.dependencies import get_current_user
from agentops_api.db.session import get_db
from agentops_api.db.repositories import find_owned_agent
from agentops_api.models.agent import Agent
from agentops_api.models.user import User
from agentops_api.schemas.entities import AgentCreate, AgentOut, AgentUpdate

router = APIRouter(prefix='/agents', tags=['agents'])


def owned_agent(db: Session, user_id: str, agent_id: str) -> Agent:
    agent = find_owned_agent(db, user_id, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found.')
    return agent


@router.get('')
def list_agents(page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100), q: str | None = Query(default=None, max_length=120), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Agent).where(Agent.user_id == user.id)
    if q:
        stmt = stmt.where(Agent.name.ilike(f'%{q.strip()}%'))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Agent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {'items': rows, 'total': total, 'page': page, 'page_size': page_size}


@router.post('', response_model=AgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(body: AgentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = Agent(user_id=user.id, name=body.name.strip(), description=body.description.strip(), environment=body.environment, framework=body.framework)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get('/{agent_id}', response_model=AgentOut)
def get_agent(agent_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return owned_agent(db, user.id, agent_id)


@router.patch('/{agent_id}', response_model=AgentOut)
def update_agent(agent_id: str, body: AgentUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = owned_agent(db, user.id, agent_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        if key == 'active':
            agent.status = 'active' if value else 'paused'
        setattr(agent, key, value)
    db.commit()
    db.refresh(agent)
    return agent


@router.delete('/{agent_id}', status_code=204)
def delete_agent(agent_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = owned_agent(db, user.id, agent_id)
    db.delete(agent)
    db.commit()
