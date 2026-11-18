import asyncio
import json
import logging
from sqlalchemy import delete, select
from agentops_api.db.session import SessionLocal
from agentops_api.evaluation.rules import evaluate_case
from agentops_api.models.dataset import DatasetCase
from agentops_api.models.evaluation import EvalResult, EvalRun
from agentops_api.models.trace import Trace
from agentops_api.providers.adapters import judge

log = logging.getLogger('agentops.evaluation')


def _llm_result(case: DatasetCase, actual: str) -> dict:
    from agentops_api.config import settings
    provider = 'groq' if settings.groq_api_key else 'gemini'
    rubric = {
        'input': case.input,
        'expected_output': case.expected_output,
        'reference_context': case.reference_context,
        'instructions': case.instructions,
        'actual_output': actual,
        'expected_tool': case.expected_tool,
        'actual_tool': case.actual_tool,
        'response_format': {'score': 'number 0..1', 'metrics': 'object of number scores', 'reasoning': 'short string'},
    }
    content = asyncio.run(judge(provider, 'Evaluate the agent response using only the supplied evidence. Return strict JSON, no markdown. Penalize unsupported claims. Data: ' + json.dumps(rubric, ensure_ascii=False)))
    parsed = json.loads(content)
    score = float(parsed.get('score', 0))
    if not 0 <= score <= 1:
        raise ValueError('Judge returned a score outside 0..1.')
    metric_values = parsed.get('metrics') if isinstance(parsed.get('metrics'), dict) else {}
    return {
        'score': round(score, 4),
        'metrics': {str(key): round(float(value), 4) for key, value in metric_values.items() if isinstance(value, (int, float)) and 0 <= value <= 1},
        'passed': score >= 0.7,
        'reasoning': str(parsed.get('reasoning', 'LLM judge returned no explanation.'))[:2000],
    }


def mark_evaluation_failed(run_id: str, error: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(EvalRun, run_id)
        if run:
            run.status = 'failed'
            run.error = error[:1000]
            db.commit()
    finally:
        db.close()


def run_evaluation(run_id: str, *, raise_on_error: bool = False) -> None:
    """Evaluate a dataset; Celery callers opt into exceptions for bounded task retries."""
    db = SessionLocal()
    try:
        run = db.get(EvalRun, run_id)
        if not run:
            log.warning('evaluation run missing', extra={'run_id': run_id})
            return
        run.status = 'running'
        run.progress = 0
        run.completed_cases = 0
        run.total_cases = 0
        run.average_score = 0.0
        run.error = None
        db.execute(delete(EvalResult).where(EvalResult.run_id == run.id))
        db.commit()
        cases = db.scalars(select(DatasetCase).where(DatasetCase.dataset_id == run.dataset_id).order_by(DatasetCase.created_at)).all()
        run.total_cases = len(cases)
        db.commit()
        if not cases:
            run.status = 'failed'
            run.error = 'This dataset has no test cases.'
            run.progress = 100
            db.commit()
            return
        run_config = run.metrics if isinstance(run.metrics, dict) else {}
        selected = run_config.get('selected', [])
        evaluator = run_config.get('evaluator', 'rules')
        matched: dict[str, str] = {}
        if run.agent_id:
            recent = db.scalars(select(Trace).where(Trace.user_id == run.user_id, Trace.agent_id == run.agent_id).order_by(Trace.started_at.desc())).all()
            for trace in recent:
                if trace.input is not None and trace.output is not None:
                    matched.setdefault(trace.input, trace.output)
        scores: list[float] = []
        totals: dict[str, list[float]] = {}
        for index, case in enumerate(cases, 1):
            actual = case.actual_output or matched.get(case.input) or ''
            result = _llm_result(case, actual) if evaluator == 'llm_judge' else evaluate_case(case, selected, actual_output=actual)
            if not actual:
                result['reasoning'] = 'No actual output is attached to this test case or matching agent trace; metrics score zero until output is supplied.'
            scores.append(result['score'])
            for key, value in result['metrics'].items():
                totals.setdefault(key, []).append(value)
            db.add(EvalResult(run_id=run.id, case_id=case.id, score=result['score'], metrics=result['metrics'], passed=result['passed'], reasoning=result['reasoning']))
            run.completed_cases = index
            run.progress = int(index * 100 / len(cases))
            db.commit()
        run.average_score = sum(scores) / len(scores)
        run.metrics = {**run_config, 'aggregate': {key: round(sum(values) / len(values), 4) for key, values in totals.items() if values}}
        run.status = 'completed'
        run.progress = 100
        run.error = None
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(EvalRun, run_id)
        if run:
            run.status = 'queued' if raise_on_error else 'failed'
            run.error = str(exc)[:1000]
            if raise_on_error:
                run.progress = 0
                run.completed_cases = 0
                run.average_score = 0.0
            db.commit()
        log.exception('evaluation failed', extra={'run_id': run_id})
        if raise_on_error:
            raise
    finally:
        db.close()
