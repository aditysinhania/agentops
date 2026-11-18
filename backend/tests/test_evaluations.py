import json
import pytest
from conftest import auth, register
from agentops_api.config import settings
from agentops_api.services import run_eval as evaluation_service


def test_dataset_import_and_evaluation_run(client):
    account = register(client)
    headers = auth(account['access_token'])
    dataset = client.post('/api/datasets', headers=headers, json={'name': 'Capital facts', 'description': 'Grounded QA'}).json()
    imported = client.post(f"/api/datasets/{dataset['id']}/import", headers=headers, files={'file': ('cases.json', '[{"input":"capital of France","expected_output":"Paris","actual_output":"Paris is the capital of France.","reference_context":"Paris is the capital of France.","structured_schema":{"type":"object","required":["answer"]},"metadata":{"source":"fixture"}}]', 'application/json')})
    assert imported.status_code == 200, imported.text
    assert imported.json()['imported'] == 1
    detail = client.get(f"/api/datasets/{dataset['id']}", headers=headers).json()
    assert len(detail['cases']) == 1
    assert detail['cases'][0]['metadata_json'] == {'source': 'fixture'}
    assert detail['cases'][0]['structured_schema']['required'] == ['answer']
    run = client.post('/api/evaluations', headers=headers, json={'dataset_id': dataset['id'], 'name': 'Offline rules', 'evaluator': 'rules'})
    assert run.status_code == 202, run.text
    result = client.get(f"/api/evaluations/{run.json()['id']}", headers=headers)
    assert result.status_code == 200
    assert result.json()['status'] == 'completed'
    assert result.json()['completed_cases'] == 1
    assert len(result.json()['results']) == 1
    assert result.json()['results'][0]['metrics']['correctness'] > 0
    other = auth(register(client, 'other@example.com')['access_token'])
    assert client.get(f"/api/evaluations/{run.json()['id']}", headers=other).status_code == 404
    assert client.get(f"/api/datasets/{dataset['id']}", headers=other).status_code == 404
    csv_dataset = client.post('/api/datasets', headers=headers, json={'name': 'CSV import cases'}).json()
    csv_import = client.post(f"/api/datasets/{csv_dataset['id']}/import", headers=headers, files={'file': ('cases.csv', 'input,expected_output,actual_output\n"capital?","Paris","Paris"\n', 'text/csv')})
    assert csv_import.status_code == 200, csv_import.text
    assert client.get(f"/api/datasets/{csv_dataset['id']}", headers=headers).json()['cases'][0]['actual_output'] == 'Paris'


def test_llm_judge_requires_explicit_server_key(client):
    account = register(client)
    headers = auth(account['access_token'])
    dataset = client.post('/api/datasets', headers=headers, json={'name': 'Judge data'}).json()
    response = client.post('/api/evaluations', headers=headers, json={'dataset_id': dataset['id'], 'name': 'Judge', 'evaluator': 'llm_judge'})
    assert response.status_code == 400
    assert 'GROQ_API_KEY or GEMINI_API_KEY' in response.json()['detail']


def test_llm_judge_uses_mocked_provider_response(client, monkeypatch):
    account = register(client)
    headers = auth(account['access_token'])
    dataset = client.post('/api/datasets', headers=headers, json={'name': 'Mocked judge'}).json()
    client.post(f"/api/datasets/{dataset['id']}/cases", headers=headers, json={
        'input': 'capital of France', 'expected_output': 'Paris', 'actual_output': 'Paris', 'reference_context': 'Paris is the capital of France.'
    })
    monkeypatch.setattr(settings, 'groq_api_key', 'test-key-never-used-for-network')
    called = []

    async def fake_judge(provider, prompt):
        called.append((provider, prompt))
        return json.dumps({'score': 0.95, 'metrics': {'correctness': 0.95}, 'reasoning': 'Mock response is grounded.'})

    monkeypatch.setattr(evaluation_service, 'judge', fake_judge)
    response = client.post('/api/evaluations', headers=headers, json={'dataset_id': dataset['id'], 'name': 'Mocked judge run', 'evaluator': 'llm_judge'})
    assert response.status_code == 202, response.text
    result = client.get(f"/api/evaluations/{response.json()['id']}", headers=headers).json()
    assert result['status'] == 'completed'
    assert result['results'][0]['score'] == 0.95
    assert result['results'][0]['reasoning'] == 'Mock response is grounded.'
    assert called and called[0][0] == 'groq'
    assert 'capital of France' in called[0][1]


def test_rule_evaluation_uses_matching_agent_trace_output(client):
    account = register(client)
    headers = auth(account['access_token'])
    agent = client.post('/api/agents', headers=headers, json={'name': 'Trace-backed agent'}).json()
    api_key = client.post('/api/api-keys', headers=headers, json={'name': 'Trace-backed evaluation'}).json()['key']
    ingested = client.post('/api/telemetry/traces', headers={'Authorization': f'Bearer {api_key}'}, json={
        'agent_id': agent['id'], 'trace_id': 'trace-backed-case-01', 'input': 'capital of France', 'output': 'Paris', 'status': 'success'
    })
    assert ingested.status_code == 202
    dataset = client.post('/api/datasets', headers=headers, json={'name': 'Trace-backed cases'}).json()
    client.post(f"/api/datasets/{dataset['id']}/cases", headers=headers, json={
        'input': 'capital of France', 'expected_output': 'Paris', 'reference_context': 'Paris is the capital of France.'
    })
    response = client.post('/api/evaluations', headers=headers, json={'dataset_id': dataset['id'], 'agent_id': agent['id'], 'name': 'Use recorded trace'})
    result = client.get(f"/api/evaluations/{response.json()['id']}", headers=headers).json()
    assert result['status'] == 'completed'
    assert result['results'][0]['metrics']['correctness'] == 1.0
    assert 'No actual output' not in result['results'][0]['reasoning']


def test_failed_celery_attempt_is_safe_to_retry(client, monkeypatch):
    account = register(client)
    headers = auth(account['access_token'])
    dataset = client.post('/api/datasets', headers=headers, json={'name': 'Retry data'}).json()
    client.post(f"/api/datasets/{dataset['id']}/cases", headers=headers, json={'input': 'question', 'expected_output': 'answer', 'actual_output': 'answer'})
    response = client.post('/api/evaluations', headers=headers, json={'dataset_id': dataset['id'], 'name': 'Retryable run'})
    run_id = response.json()['id']
    original_evaluate_case = evaluation_service.evaluate_case

    def transient_failure(*_args, **_kwargs):
        raise RuntimeError('simulated provider timeout')

    monkeypatch.setattr(evaluation_service, 'evaluate_case', transient_failure)
    with pytest.raises(RuntimeError, match='simulated provider timeout'):
        evaluation_service.run_evaluation(run_id, raise_on_error=True)
    db = client.app.state.TestingSession()
    try:
        failed_attempt = client.get(f'/api/evaluations/{run_id}', headers=headers).json()
        assert failed_attempt['status'] == 'queued'
        assert failed_attempt['completed_cases'] == 0
        assert failed_attempt['results'] == []
    finally:
        db.close()

    monkeypatch.setattr(evaluation_service, 'evaluate_case', original_evaluate_case)
    evaluation_service.run_evaluation(run_id, raise_on_error=True)
    recovered = client.get(f'/api/evaluations/{run_id}', headers=headers).json()
    assert recovered['status'] == 'completed'
    assert recovered['completed_cases'] == 1
    assert len(recovered['results']) == 1


def test_prompt_linked_runs_feed_regression_comparisons(client):
    account = register(client)
    headers = auth(account['access_token'])
    agent = client.post('/api/agents', headers=headers, json={'name': 'Regression agent'}).json()
    version_one = client.post('/api/prompts', headers=headers, json={'agent_id': agent['id'], 'label': 'Baseline', 'content': 'Answer with evidence.'})
    version_two = client.post('/api/prompts', headers=headers, json={'agent_id': agent['id'], 'label': 'Refined', 'content': 'Answer with evidence. Be concise.', 'regression_threshold': 0.05})
    assert version_one.status_code == 201
    assert version_two.status_code == 201
    dataset = client.post('/api/datasets', headers=headers, json={'name': 'Prompt regression data'}).json()
    case = client.post(f"/api/datasets/{dataset['id']}/cases", headers=headers, json={
        'input': 'capital of France', 'expected_output': 'Paris', 'actual_output': 'Paris', 'reference_context': 'Paris is the capital of France.'
    }).json()
    linked_runs = []
    for index, prompt in enumerate((version_one.json(), version_two.json())):
        response = client.post('/api/evaluations', headers=headers, json={
            'dataset_id': dataset['id'], 'agent_id': agent['id'], 'prompt_version_id': prompt['id'], 'name': f"Prompt v{prompt['version']}"
        })
        assert response.status_code == 202, response.text
        linked_runs.append(client.get(f"/api/evaluations/{response.json()['id']}", headers=headers).json())
        assert linked_runs[-1]['prompt_version_id'] == prompt['id']
        assert linked_runs[-1]['status'] == 'completed'
        if index == 0:
            degraded = client.patch(f"/api/datasets/{dataset['id']}/cases/{case['id']}", headers=headers, json={'actual_output': 'Atlantis'})
            assert degraded.status_code == 200
    comparisons = client.get('/api/analytics/regressions', headers=headers).json()['items']
    assert len(comparisons) == 1
    assert comparisons[0]['from_version'] == 1
    assert comparisons[0]['to_version'] == 2
    assert comparisons[0]['status'] == 'regression'
    assert comparisons[0]['delta'] < -comparisons[0]['threshold']


def test_prompt_pair_without_runs_is_not_evaluated(client):
    account = register(client)
    headers = auth(account['access_token'])
    agent = client.post('/api/agents', headers=headers, json={'name': 'Pending comparison agent'}).json()
    for label in ('Version one', 'Version two'):
        assert client.post('/api/prompts', headers=headers, json={'agent_id': agent['id'], 'label': label, 'content': label}).status_code == 201
    comparisons = client.get('/api/analytics/regressions', headers=headers).json()['items']
    assert len(comparisons) == 1
    assert comparisons[0]['status'] == 'not_evaluated'
    assert comparisons[0]['baseline_score'] is None and comparisons[0]['current_score'] is None
