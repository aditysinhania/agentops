import os
os.environ.setdefault('AGENTOPS_DEMO_MODE', 'true')
os.environ.setdefault('SECRET_KEY', 'test-only-secret-do-not-use-in-production')

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from agentops_api.db.base import Base
from agentops_api.db.session import get_db
from agentops_api.main import app, _buckets
import agentops_api.services.run_eval as evaluation_service


@pytest.fixture
def client(monkeypatch):
    _buckets.clear()
    test_engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(test_engine)
    app.state.TestingSession = TestingSession

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(evaluation_service, 'SessionLocal', TestingSession)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    _buckets.clear()
    test_engine.dispose()
    del app.state.TestingSession


def register(client, email='owner@example.com'):
    response = client.post('/api/auth/register', json={'email': email, 'full_name': 'Test Owner', 'password': 'test-password-123'})
    assert response.status_code == 201, response.text
    return response.json()


def auth(token):
    return {'Authorization': f'Bearer {token}'}
