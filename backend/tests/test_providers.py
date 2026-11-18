import asyncio
from agentops_api.providers import adapters


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    calls = []
    response_payload = {}

    def __init__(self, timeout):
        assert timeout.connect == 5.0
        assert timeout.read == 20.0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.response_payload)


def test_groq_and_gemini_adapters_use_mocked_responses(monkeypatch):
    FakeAsyncClient.calls.clear()
    monkeypatch.setattr(adapters.httpx, 'AsyncClient', FakeAsyncClient)
    monkeypatch.setattr(adapters.settings, 'groq_api_key', 'not-a-real-groq-key')
    monkeypatch.setattr(adapters.settings, 'groq_model', 'mock-groq-model')
    monkeypatch.setattr(adapters.settings, 'gemini_api_key', 'not-a-real-gemini-key')
    monkeypatch.setattr(adapters.settings, 'gemini_model', 'mock-gemini-model')

    FakeAsyncClient.response_payload = {'choices': [{'message': {'content': 'groq mock response'}}]}
    assert asyncio.run(adapters.judge('groq', 'evaluate this')) == 'groq mock response'
    groq_url, groq_options = FakeAsyncClient.calls[-1]
    assert groq_url == 'https://api.groq.com/openai/v1/chat/completions'
    assert groq_options['headers']['Authorization'] == 'Bearer not-a-real-groq-key'
    assert groq_options['json']['model'] == 'mock-groq-model'

    FakeAsyncClient.response_payload = {'candidates': [{'content': {'parts': [{'text': 'gemini mock response'}]}}]}
    assert asyncio.run(adapters.judge('gemini', 'evaluate this')) == 'gemini mock response'
    gemini_url, gemini_options = FakeAsyncClient.calls[-1]
    assert '/models/mock-gemini-model:generateContent' in gemini_url
    assert gemini_options['params']['key'] == 'not-a-real-gemini-key'
