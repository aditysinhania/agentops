# AgentOps

AgentOps is an AI-agent reliability workbench: register runtimes, collect traces, curate evaluation cases, compare prompt versions, and inspect performance and estimated cost. The repository contains an integrated React dashboard, FastAPI backend, Python telemetry SDK, deterministic evaluation engine, optional Groq/Gemini judges, and PostgreSQL/Redis/Celery deployment via Docker Compose.

## Architecture

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts and Lucide. The app uses same-origin `/api` calls; Vite proxies these to FastAPI during development. The production FastAPI process serves the compiled SPA.
- **API:** FastAPI and Pydantic; SQLAlchemy 2.x normalized entities with ownership-scoped repository queries; Alembic-managed schema; JWT application sessions; bcrypt password hashes; ownership checks on every user resource. The app never stores raw API keys. Keys are displayed once and stored as a digest.
- **Persistence:** PostgreSQL 16 is the supported Compose/production-style database. Schema changes are committed migrations; app startup does not call `create_all`. For a cloud Preview that has no compatible Postgres server, set `AGENTOPS_DEMO_MODE=true` to use a clearly identified SQLite demo database. Do not use the Webdev managed database for this app: that service is MySQL-compatible, not PostgreSQL.
- **Evaluation:** Offline, deterministic rule checks for correctness/relevance/contextual accuracy/instruction following/hallucination/tool selection/structured output. This is a transparent heuristic baseline, not a claim of semantic proof. Optional LLM judging uses the configured Groq or Gemini key. No provider calls are needed for tests or rule runs.
- **Jobs:** Local preview uses FastAPI background tasks. Compose runs evaluation tasks on Celery with Redis; progress/results live in PostgreSQL. Redis is optional managed infrastructure and is deliberately not enabled for this project.
- **Observability:** Trace rows and nested span rows store input/output/error, times, token counts, metadata and cost. Ingest is API-key authenticated; SDK transport is bounded, asynchronous and fail-open.

## Requirements

For Compose: Docker Engine with Compose v2. For local development: Python 3.11+, Node 22+, pnpm 11.25.0, and PostgreSQL 16 if using the PostgreSQL path. Redis is needed for Celery mode; no paid LLM access is needed for tests/rule scoring.

## Run the full stack (recommended)

```bash
cp .env.example .env
# Edit SECRET_KEY and POSTGRES_PASSWORD in .env before exposing the service.
docker compose up --build
```

The app is available at `http://localhost:3000`, OpenAPI docs at `http://localhost:3000/api/docs`, and health at `/healthz`. PostgreSQL data is persisted in `postgres_data`; Redis data is persisted in `redis_data`. `docker compose logs -f api worker` shows service output. Stop services with `docker compose down`; to retain database data, do not add `-v`. To intentionally remove local test state, `docker compose down -v` deletes local volumes.

The Compose example uses development-only local database credentials. Replace them and `SECRET_KEY` before any shared/public deployment. Restrict CORS to the actual frontend origin.

## Local development

Install dependencies once:

```bash
pnpm install
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
pip install --no-deps -e sdk
```

Set `DATABASE_URL` to your local PostgreSQL DSN and a strong `SECRET_KEY`. Apply migrations and start the API:

```bash
export PYTHONPATH=backend:sdk
export DATABASE_URL='postgresql+psycopg://agentops:password@localhost:5432/agentops'
export SECRET_KEY='replace-with-a-long-random-secret'
.venv/bin/alembic -c backend/alembic.ini upgrade head
.venv/bin/uvicorn agentops_api.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

In another terminal start Vite, which serves port 3000 and proxies `/api` to 8000:

```bash
pnpm dev
```

If no Postgres is available for a disposable preview, run the API with `AGENTOPS_DEMO_MODE=true`. This selects `/tmp/agentops-preview.db` and bypasses the platform's incompatible MySQL `DATABASE_URL`; it is not a durable production configuration. Apply Alembic first:

```bash
AGENTOPS_DEMO_MODE=true PYTHONPATH=backend .venv/bin/alembic -c backend/alembic.ini upgrade head
AGENTOPS_DEMO_MODE=true PYTHONPATH=backend:sdk .venv/bin/uvicorn agentops_api.main:app --host 0.0.0.0 --port 8000 --reload
```

Create your account at `/register`; then use the dashboard's Agents page to register a runtime and API Keys to issue an SDK credential.

## Instrument a Python agent

Install the local SDK (or package `sdk/` for internal distribution), then export the workspace API key, agent UUID and API endpoint in the agent runtime:

```bash
export AGENTOPS_API_KEY='ao_live_...'
export AGENTOPS_AGENT_ID='<agent UUID from Agent Details>'
export AGENTOPS_ENDPOINT='http://localhost:8000'
PYTHONPATH=sdk python examples/sample_agent.py
```

The SDK is dependency-free and provides context-managed traces, nested spans, LLM/tool helpers, token counts and metadata:

```python
from agentops import AgentOps

ops = AgentOps()
with ops.trace('support.answer', input='How do I reset access?') as run:
    with run.tool_call('account.lookup', input={'user_id': 'u-42'}) as tool:
        tool.set_output({'eligible': True})
    with run.llm_call('draft.reply', model='provider-model') as call:
        answer = 'Use the reset link in your account email.'
        call.set_output(answer)
        call.set_tokens(input_tokens=26, output_tokens=12)
    run.set_output(answer)
```

Telemetry sends in a daemon worker with a bounded timeout; unreachable AgentOps endpoints are deliberately swallowed so the application continues. Callers should avoid including secrets or regulated personal data in telemetry. Inputs, outputs, errors and metadata may contain sensitive content; apply your own redaction before instrumentation.

## Datasets and evaluation

Create a dataset, add test cases manually or import a `.csv`/`.json` file up to 5 MB (maximum 1,000 rows). Supported case fields include `input`, `expected_output`, `actual_output`, `reference_context`, `expected_tool`, `actual_tool`, `instructions`, `structured_schema` and `metadata`. A run evaluates the stored `actual_output`, or the latest trace output for the selected agent when the trace input exactly matches the case input. Missing outputs are explicitly scored as zero and described in the result reason; AgentOps does not fabricate an answer or run arbitrary user code.

Rule runs need no provider key. For LLM judging, set `GROQ_API_KEY` or `GEMINI_API_KEY` only in the backend environment (never in frontend code), choose the LLM-judge option and run the evaluation. Provider models are configurable through `GROQ_MODEL` and `GEMINI_MODEL`. Provider API usage may incur provider charges; tests mock judge responses and make no paid calls.

## REST API overview

Every application endpoint is under `/api`; interactive OpenAPI is `/api/docs`.

| Area | Routes |
| --- | --- |
| Authentication | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Agents | `GET/POST /agents`, `GET/PATCH/DELETE /agents/{id}` |
| SDK telemetry | `POST /telemetry/traces` (Bearer `ao_live_…` key) |
| Traces | `GET /traces`, `GET /traces/{id}` |
| Datasets and cases | `GET/POST /datasets`, `GET/PATCH/DELETE /datasets/{id}`, `POST /datasets/{id}/cases`, `PATCH/DELETE /datasets/{id}/cases/{case_id}`, `POST /datasets/{id}/import` |
| Evaluation | `GET/POST /evaluations`, `GET /evaluations/{id}` |
| Prompts | `GET/POST /prompts` |
| Analytics | `GET /analytics/overview`, `GET /analytics/regressions` |
| Keys/settings | `GET/POST /api-keys`, `DELETE /api-keys/{id}`, `GET/PATCH /settings` |

List endpoints accept `page` and `page_size` where applicable. Authentication uses `Authorization: Bearer <JWT>`; telemetry requires an API key. Responses are user-scoped and return 404 when an owned resource is not accessible.

## Migrations

```bash
PYTHONPATH=backend .venv/bin/alembic -c backend/alembic.ini current
PYTHONPATH=backend .venv/bin/alembic -c backend/alembic.ini upgrade head
```

Create a new revision after changing models:

```bash
PYTHONPATH=backend .venv/bin/alembic -c backend/alembic.ini revision --autogenerate -m "describe schema change"
```

Review autogenerated revisions before applying. Development and published processes using the same DSN see the same data; do not run destructive migrations without a backup and explicit approval.

## Tests and build

```bash
AGENTOPS_DEMO_MODE=true PYTHONPATH=backend:sdk .venv/bin/pytest -q backend/tests
pnpm build
```

The tests use isolated temporary SQLite databases and mocked provider responses. They do not require Docker, Redis, Groq/Gemini keys, or paid LLM calls.

## Security and configuration

- Use a unique strong `SECRET_KEY` outside local development; production startup rejects the built-in local-only value.
- Keep `GROQ_API_KEY`, `GEMINI_API_KEY`, `DATABASE_URL`, `REDIS_URL` and API keys on the server/runtime only.
- The dashboard stores its short-lived JWT in `sessionStorage`; sign out clears it. Passwords use bcrypt and are bounded to 72 UTF-8 bytes; provider values are never returned to the browser.
- The API includes request IDs, structured request logs, an in-process rate limiter, timeouts for external calls, bounded import sizes and centralized generic server-error responses. Use an upstream gateway/WAF and shared rate-limit store for horizontally scaled production.
- Configure CORS intentionally. Do not send secrets or sensitive data in trace payloads without applying an appropriate retention/redaction policy.

## Platform notes

The hosted preview is configured as a website, but the project explicitly targets PostgreSQL. Its managed database feature is MySQL-compatible, so it is not used as a substitute. Hosted Preview can use the opt-in SQLite demo fallback; durable multi-user deployment should use the included Compose stack or a user-selected PostgreSQL host. Managed Redis was not enabled; the supplied Compose configuration provides local Redis and Celery.
