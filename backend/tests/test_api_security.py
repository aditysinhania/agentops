import hashlib
from sqlalchemy import select
from agentops_api.models.user import ApiKey
from conftest import auth, register


def test_password_login_and_duplicate_registration(client):
    account = register(client)
    assert account['user']['email'] == 'owner@example.com'
    login = client.post('/api/auth/login', json={'email': 'owner@example.com', 'password': 'test-password-123'})
    assert login.status_code == 200
    assert client.get('/api/auth/me', headers=auth(login.json()['access_token'])).json()['id'] == account['user']['id']
    assert client.post('/api/auth/login', json={'email': 'owner@example.com', 'password': 'wrong-password'}).status_code == 401
    assert client.post('/api/auth/register', json={'email': 'owner@example.com', 'full_name': 'Duplicate', 'password': 'test-password-123'}).status_code == 409


def test_passwords_exceeding_bcrypt_utf8_limit_are_rejected(client):
    headers = {'email': 'long-password@example.com', 'full_name': 'Long Password', 'password': 'é' * 37}
    assert client.post('/api/auth/register', json=headers).status_code == 422
    assert client.post('/api/auth/login', json={'email': headers['email'], 'password': headers['password']}).status_code == 422


def test_user_cannot_read_another_users_agent(client):
    first = register(client, 'first@example.com')
    second = register(client, 'second@example.com')
    created = client.post('/api/agents', headers=auth(first['access_token']), json={'name': 'Private agent', 'framework': 'custom'})
    assert created.status_code == 201
    denied = client.get(f"/api/agents/{created.json()['id']}", headers=auth(second['access_token']))
    assert denied.status_code == 404
    assert client.get('/api/agents', headers=auth(second['access_token'])).json()['items'] == []


def test_api_key_is_shown_once_and_telemetry_is_ingested(client):
    account = register(client)
    agent = client.post('/api/agents', headers=auth(account['access_token']), json={'name': 'SDK agent'}).json()
    created = client.post('/api/api-keys', headers=auth(account['access_token']), json={'name': 'Local sample'}).json()
    raw = created['key']
    assert raw.startswith('ao_live_')
    listing = client.get('/api/api-keys', headers=auth(account['access_token'])).json()['items']
    assert 'key' not in listing[0]
    db = client.app.state.TestingSession()
    try:
        key_record = db.scalar(select(ApiKey).where(ApiKey.id == created['id']))
        assert key_record.key_hash == hashlib.sha256(raw.encode()).hexdigest()
        assert raw not in key_record.key_hash
    finally:
        db.close()
    ingested = client.post('/api/telemetry/traces', headers={'Authorization': f'Bearer {raw}'}, json={
        'agent_id': agent['id'], 'trace_id': 'trace-test-0001', 'name': 'answer', 'status': 'success',
        'input': 'hello', 'output': 'world', 'latency_ms': 23.5, 'input_tokens': 2, 'output_tokens': 1,
        'metadata': {'environment': 'test'},
        'spans': [{'span_id': 'root-1', 'kind': 'llm', 'name': 'respond', 'status': 'success', 'latency_ms': 10}],
    })
    assert ingested.status_code == 202, ingested.text
    assert ingested.json()['accepted'] is True
    traces = client.get('/api/traces', headers=auth(account['access_token'])).json()
    assert traces['total'] == 1
    assert traces['items'][0]['agent_name'] == 'SDK agent'
    assert traces['items'][0]['metadata_json']['environment'] == 'test'
    detail = client.get(f"/api/traces/{traces['items'][0]['id']}", headers=auth(account['access_token'])).json()
    assert len(detail['spans']) == 1
    overview = client.get('/api/analytics/overview', headers=auth(account['access_token'])).json()
    assert overview['executions'] == 1
    assert overview['tokens'] == 3
    assert overview['success_rate'] == 100.0
    assert client.post('/api/telemetry/traces', headers={'Authorization': f'Bearer {raw}'}, json={'agent_id': agent['id'], 'trace_id': 'trace-test-0001'}).json()['duplicate'] is True
