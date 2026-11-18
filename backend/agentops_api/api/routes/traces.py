from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from agentops_api.auth.dependencies import get_api_key_user, get_current_user
from agentops_api.config import settings
from agentops_api.db.session import get_db
from agentops_api.models.agent import Agent
from agentops_api.models.trace import Span, Trace
from agentops_api.models.user import User
from agentops_api.schemas.entities import TraceIn

router = APIRouter(prefix='/traces', tags=['traces'])
telemetry_router = APIRouter(prefix='/telemetry', tags=['telemetry'])


def _columns_dict(instance):
    """Serialize mapped columns by their database names without ORM relationships."""
    return {prop.key: getattr(instance, prop.key) for prop in instance.__mapper__.column_attrs}


@router.get('')
def list_traces(page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100), agent_id: str | None = None, status_filter: str | None = Query(default=None, alias='status'), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Trace).where(Trace.user_id == user.id)
    if agent_id:
        stmt = stmt.where(Trace.agent_id == agent_id)
    if status_filter:
        stmt = stmt.where(Trace.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Trace.started_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    agent_ids = {row.agent_id for row in rows}
    agents = {a.id: a.name for a in db.scalars(select(Agent).where(Agent.id.in_(agent_ids))).all()} if agent_ids else {}
    items = [{**_columns_dict(row), 'agent_name': agents.get(row.agent_id, 'Unknown')} for row in rows]
    return {'items': items, 'total': total, 'page': page, 'page_size': page_size}


@router.get('/{trace_pk}')
def get_trace(trace_pk: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trace = db.scalar(select(Trace).options(selectinload(Trace.spans)).where(Trace.id == trace_pk, Trace.user_id == user.id))
    if not trace:
        raise HTTPException(status_code=404, detail='Trace not found.')
    return {'trace': _columns_dict(trace), 'spans': [_columns_dict(span) for span in trace.spans]}


@telemetry_router.post('/traces', status_code=status.HTTP_202_ACCEPTED)
def ingest_trace(body: TraceIn, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, api_key = get_api_key_user(authorization, db)
    agent = db.scalar(select(Agent).where(Agent.id == body.agent_id, Agent.user_id == user.id))
    if not agent or not agent.active:
        raise HTTPException(status_code=404, detail='Active agent not found for this API key owner.')
    existing = db.scalar(select(Trace).where(Trace.user_id == user.id, Trace.trace_id == body.trace_id))
    if existing:
        return {'id': existing.id, 'trace_id': existing.trace_id, 'accepted': True, 'duplicate': True}
    rates = user.settings_json or {}
    input_rate = float(rates.get('cost_input_per_1k', settings.cost_per_1k_input_tokens))
    output_rate = float(rates.get('cost_output_per_1k', settings.cost_per_1k_output_tokens))
    input_cost = input_rate * body.input_tokens / 1000
    output_cost = output_rate * body.output_tokens / 1000
    trace = Trace(user_id=user.id, agent_id=agent.id, trace_id=body.trace_id, name=body.name, status=body.status, input=body.input, output=body.output, error=body.error, started_at=body.started_at or datetime.now(timezone.utc), ended_at=body.ended_at, latency_ms=body.latency_ms, input_tokens=body.input_tokens, output_tokens=body.output_tokens, cost_usd=input_cost + output_cost, metadata_json=body.metadata)
    db.add(trace)
    for item in body.spans:
        db.add(Span(trace=trace, span_id=item.span_id, parent_span_id=item.parent_span_id, kind=item.kind, name=item.name, status=item.status, input=item.input, output=item.output, error=item.error, started_at=item.started_at or datetime.now(timezone.utc), ended_at=item.ended_at, latency_ms=item.latency_ms, input_tokens=item.input_tokens, output_tokens=item.output_tokens, attributes=item.attributes))
    api_key.last_used_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {'id': trace.id, 'trace_id': trace.trace_id, 'accepted': True, 'duplicate': False}
