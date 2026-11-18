from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Span:
    def __init__(self, name: str, kind: str = 'agent', parent_span_id: str | None = None, input: Any = None, attributes: dict[str, Any] | None = None):
        self.span_id = uuid.uuid4().hex
        self.parent_span_id = parent_span_id
        self.kind = kind
        self.name = name[:160]
        self.started_at = _now()
        self._started = time.perf_counter()
        self.input = input
        self.output: Any = None
        self.error: str | None = None
        self.status = 'success'
        self.input_tokens = 0
        self.output_tokens = 0
        self.attributes = dict(attributes or {})
        self.ended_at: str | None = None
        self.latency_ms = 0.0

    def set_output(self, output: Any) -> None:
        self.output = output

    def set_tokens(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.input_tokens = max(0, int(input_tokens))
        self.output_tokens = max(0, int(output_tokens))

    def add_metadata(self, **values: Any) -> None:
        self.attributes.update(values)

    def finish(self, error: BaseException | None = None) -> None:
        self.ended_at = _now()
        self.latency_ms = round((time.perf_counter() - self._started) * 1000, 3)
        if error is not None:
            self.status = 'error'
            self.error = f'{type(error).__name__}: {error}'[:4000]

    def payload(self) -> dict[str, Any]:
        return {'span_id': self.span_id, 'parent_span_id': self.parent_span_id, 'kind': self.kind, 'name': self.name, 'status': self.status, 'input': _serialize(self.input), 'output': _serialize(self.output), 'error': self.error, 'started_at': self.started_at, 'ended_at': self.ended_at, 'latency_ms': self.latency_ms, 'input_tokens': self.input_tokens, 'output_tokens': self.output_tokens, 'attributes': self.attributes}


def _serialize(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value[:12000]
    try:
        return json.dumps(value, ensure_ascii=False, default=str)[:12000]
    except Exception:
        return str(value)[:12000]


class TraceRun:
    def __init__(self, client: 'AgentOps', name: str, input: Any = None, metadata: dict[str, Any] | None = None):
        self.client = client
        self.trace_id = uuid.uuid4().hex
        self.name = name[:160]
        self.input = input
        self.output: Any = None
        self.error: str | None = None
        self.status = 'success'
        self.started_at = _now()
        self._started = time.perf_counter()
        self._span_stack: list[Span] = []
        self._spans: list[Span] = []
        self._metadata = dict(metadata or {})
        self.input_tokens = 0
        self.output_tokens = 0

    def __enter__(self) -> 'TraceRun':
        return self

    def __exit__(self, exc_type, exc, _tb) -> bool:
        while self._span_stack:
            span = self._span_stack.pop()
            span.finish(exc)
        ended = _now()
        latency = round((time.perf_counter() - self._started) * 1000, 3)
        if exc is not None:
            self.status = 'error'
            self.error = f'{exc_type.__name__}: {exc}'[:4000]
        self.client._send({'agent_id': self.client.agent_id, 'trace_id': self.trace_id, 'name': self.name, 'status': self.status, 'input': _serialize(self.input), 'output': _serialize(self.output), 'error': self.error, 'started_at': self.started_at, 'ended_at': ended, 'latency_ms': latency, 'input_tokens': self.input_tokens, 'output_tokens': self.output_tokens, 'metadata': self._metadata, 'spans': [span.payload() for span in self._spans]})
        return False

    def set_output(self, output: Any) -> None:
        self.output = output

    def set_token_usage(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.input_tokens = max(0, int(input_tokens))
        self.output_tokens = max(0, int(output_tokens))

    def add_metadata(self, **values: Any) -> None:
        self._metadata.update(values)

    @contextmanager
    def span(self, name: str, *, kind: str = 'agent', input: Any = None, attributes: dict[str, Any] | None = None) -> Iterator[Span]:
        parent = self._span_stack[-1].span_id if self._span_stack else None
        span = Span(name, kind, parent, input, attributes)
        self._spans.append(span)
        self._span_stack.append(span)
        error = None
        try:
            yield span
        except BaseException as exc:
            error = exc
            raise
        finally:
            span.finish(error)
            if self._span_stack and self._span_stack[-1] is span:
                self._span_stack.pop()

    @contextmanager
    def llm_call(self, name: str, *, model: str, input: Any = None) -> Iterator[Span]:
        with self.span(name, kind='llm', input=input, attributes={'model': model}) as span:
            yield span

    @contextmanager
    def tool_call(self, name: str, *, input: Any = None) -> Iterator[Span]:
        with self.span(name, kind='tool', input=input) as span:
            yield span


class AgentOps:
    """Best-effort trace client. Network errors never escape into agent code."""
    def __init__(self, api_key: str | None = None, agent_id: str | None = None, endpoint: str | None = None, timeout: float = 0.8):
        self.api_key = api_key or os.getenv('AGENTOPS_API_KEY', '')
        self.agent_id = agent_id or os.getenv('AGENTOPS_AGENT_ID', '')
        self.endpoint = (endpoint or os.getenv('AGENTOPS_ENDPOINT', 'http://127.0.0.1:8000')).rstrip('/')
        self.timeout = max(0.1, min(float(timeout), 3.0))

    def trace(self, name: str, *, input: Any = None, metadata: dict[str, Any] | None = None) -> TraceRun:
        return TraceRun(self, name, input, metadata)

    def _send(self, payload: dict[str, Any]) -> None:
        if not self.api_key or not self.agent_id:
            return
        body = json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8')
        request = urllib.request.Request(f'{self.endpoint}/api/telemetry/traces', data=body, headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}, method='POST')
        def transmit() -> None:
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    response.read(256)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                # Observability must never bring down the observed application.
                return
            except Exception:
                return
        try:
            threading.Thread(target=transmit, name='agentops-telemetry', daemon=True).start()
        except Exception:
            return

    @contextmanager
    def instrument(self, name: str, *, input_getter=None):
        """Decorate by hand with `with ops.instrument(...) as run`; see SDK docs for wrappers."""
        with self.trace(name, input=input_getter() if input_getter else None) as run:
            yield run


__all__ = ['AgentOps', 'TraceRun', 'Span']
