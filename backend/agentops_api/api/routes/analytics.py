from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from agentops_api.auth.dependencies import get_current_user
from agentops_api.config import settings
from agentops_api.db.session import get_db
from agentops_api.models.agent import Agent
from agentops_api.models.evaluation import EvalRun
from agentops_api.models.prompt import PromptVersion
from agentops_api.models.trace import Trace
from agentops_api.models.user import User

router = APIRouter(prefix='/analytics', tags=['analytics'])


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * p)))
    return round(float(ordered[pos]), 1)


@router.get('/overview')
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=13)
    traces = db.scalars(select(Trace).where(Trace.user_id == user.id, Trace.started_at >= since)).all()
    agents = db.scalars(select(Agent).where(Agent.user_id == user.id)).all()
    runs = db.scalars(select(EvalRun).where(EvalRun.user_id == user.id, EvalRun.status == 'completed')).all()
    total = len(traces)
    success = sum(1 for t in traces if t.status.lower() in {'success', 'completed', 'ok'})
    latencies = [t.latency_ms for t in traces]
    daily: dict[str, dict] = {}
    for offset in range(13, -1, -1):
        day = (date.today() - timedelta(days=offset)).isoformat()
        daily[day] = {'date': day, 'runs': 0, 'errors': 0, 'tokens': 0}
    for trace in traces:
        day = trace.started_at.date().isoformat()
        if day not in daily:
            continue
        daily[day]['runs'] += 1
        daily[day]['errors'] += int(trace.status.lower() not in {'success', 'completed', 'ok'})
        daily[day]['tokens'] += trace.input_tokens + trace.output_tokens
    avg_score = sum(r.average_score for r in runs) / len(runs) if runs else 0.0
    return {
        'window_days': 14,
        'executions': total,
        'success_rate': round(success / total * 100, 1) if total else 0.0,
        'failure_count': total - success,
        'p50_latency_ms': percentile(latencies, .50),
        'p95_latency_ms': percentile(latencies, .95),
        'p99_latency_ms': percentile(latencies, .99),
        'tokens': sum(t.input_tokens + t.output_tokens for t in traces),
        'estimated_cost_usd': round(sum(t.cost_usd for t in traces), 5),
        'average_eval_score': round(avg_score * 100, 1),
        'active_agents': sum(1 for agent in agents if agent.active),
        'completed_evaluations': len(runs),
        'series': list(daily.values()),
        'latency_buckets': [
            {'label': 'P50', 'value': percentile(latencies, .50)},
            {'label': 'P95', 'value': percentile(latencies, .95)},
            {'label': 'P99', 'value': percentile(latencies, .99)},
        ],
        'cost_rates_per_1k': {'input': settings.cost_per_1k_input_tokens, 'output': settings.cost_per_1k_output_tokens},
    }


@router.get('/regressions')
def regressions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prompts = db.scalars(select(PromptVersion).where(PromptVersion.user_id == user.id).order_by(PromptVersion.agent_id, PromptVersion.version)).all()
    runs = db.scalars(select(EvalRun).where(EvalRun.user_id == user.id, EvalRun.status == 'completed').order_by(EvalRun.created_at.desc())).all()
    by_prompt: dict[str, list[EvalRun]] = {}
    for run in runs:
        if run.prompt_version_id:
            by_prompt.setdefault(run.prompt_version_id, []).append(run)
    output = []
    prompt_groups: dict[str, list[PromptVersion]] = {}
    for prompt in prompts:
        prompt_groups.setdefault(prompt.agent_id, []).append(prompt)
    for agent_id, versions in prompt_groups.items():
        versions.sort(key=lambda item: item.version)
        for older, newer in zip(versions, versions[1:]):
            a, b = by_prompt.get(older.id, []), by_prompt.get(newer.id, [])
            if not a or not b:
                output.append({'agent_id': agent_id, 'from_version': older.version, 'to_version': newer.version, 'baseline_score': None, 'current_score': None, 'delta': None, 'threshold': newer.regression_threshold, 'status': 'not_evaluated'})
                continue
            baseline, current = a[0].average_score, b[0].average_score
            delta = current - baseline
            output.append({'agent_id': agent_id, 'from_version': older.version, 'to_version': newer.version, 'baseline_score': round(baseline, 4), 'current_score': round(current, 4), 'delta': round(delta, 4), 'threshold': newer.regression_threshold, 'status': 'regression' if delta < -newer.regression_threshold else 'improved' if delta > newer.regression_threshold else 'stable'})
    return {'items': output}
