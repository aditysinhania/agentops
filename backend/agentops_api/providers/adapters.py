import httpx
from agentops_api.config import settings


class ProviderNotConfigured(RuntimeError):
    pass


async def judge(provider: str, prompt: str) -> str:
    timeout = httpx.Timeout(20.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        if provider == 'groq':
            if not settings.groq_api_key:
                raise ProviderNotConfigured('Set GROQ_API_KEY to use the optional Groq judge.')
            response = await client.post('https://api.groq.com/openai/v1/chat/completions', headers={'Authorization': f'Bearer {settings.groq_api_key}'}, json={'model': settings.groq_model, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0})
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        if provider == 'gemini':
            if not settings.gemini_api_key:
                raise ProviderNotConfigured('Set GEMINI_API_KEY to use the optional Gemini judge.')
            response = await client.post(f'https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent', params={'key': settings.gemini_api_key}, json={'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'temperature': 0}})
            response.raise_for_status()
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        raise ValueError('Supported judges are groq and gemini.')
