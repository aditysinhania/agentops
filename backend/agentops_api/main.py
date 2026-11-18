import json
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from agentops_api.api.router import api_router
from agentops_api.config import settings
from agentops_api.db.session import engine

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('agentops.http')
if settings.environment.lower() in {'production', 'prod'} and settings.secret_key == 'local-only-change-me-before-deploying':
    raise RuntimeError('Set a strong SECRET_KEY before starting AgentOps in production.')
app = FastAPI(title='AgentOps API', version='0.1.0', description='Trace, evaluate and improve AI agent reliability.', openapi_url='/api/openapi.json', docs_url='/api/docs', redoc_url='/api/redoc')
origins = [part.strip() for part in settings.cors_origins.split(',') if part.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins or ['*'], allow_methods=['*'], allow_headers=['Authorization', 'Content-Type', 'X-Request-ID'], allow_credentials=False)
app.include_router(api_router)
_buckets: dict[str, deque[float]] = defaultdict(deque)


@app.middleware('http')
async def request_guard_and_log(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get('x-request-id', str(uuid4()))[:64]
    ip = request.client.host if request.client else 'unknown'
    bucket_key = f'{ip}:{request.url.path}' if request.url.path.startswith('/api/auth/') else f'{ip}:global'
    now = time.monotonic()
    bucket = _buckets[bucket_key]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    limit = 12 if request.url.path in {'/api/auth/login', '/api/auth/register'} else 180
    if len(bucket) >= limit:
        response = JSONResponse(status_code=429, content={'detail': 'Rate limit exceeded. Try again shortly.', 'request_id': request_id})
    else:
        bucket.append(now)
        try:
            response = await call_next(request)
        except Exception:
            logger.exception('unhandled_request_error', extra={'request_id': request_id, 'path': request.url.path})
            response = JSONResponse(status_code=500, content={'detail': 'An unexpected server error occurred.', 'request_id': request_id})
    response.headers['X-Request-ID'] = request_id
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cache-Control'] = 'no-store'
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    logger.info(json.dumps({'event': 'http_request', 'request_id': request_id, 'method': request.method, 'path': request.url.path, 'status': response.status_code, 'latency_ms': elapsed, 'ip': ip}, separators=(',', ':')))
    return response


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_request: Request, _exc: IntegrityError):
    return JSONResponse(status_code=409, content={'detail': 'A conflicting record already exists.'})


@app.get('/healthz', tags=['health'])
def healthz():
    return {'status': 'ok'}


@app.get('/api/health', tags=['health'])
def api_health():
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        return {'status': 'ok', 'database': 'connected', 'storage_mode': 'sqlite-demo' if settings.demo_mode else engine.dialect.name}
    except Exception:
        return JSONResponse(status_code=503, content={'status': 'degraded', 'database': 'unavailable'})


_dist = Path(os.getenv('FRONTEND_DIST', str(Path(__file__).resolve().parents[2] / 'dist'))).resolve()
_index = _dist / 'index.html'
_assets = _dist / 'assets'
if _index.is_file():
    if _assets.is_dir():
        app.mount('/assets', StaticFiles(directory=_assets), name='frontend-assets')

    @app.get('/', include_in_schema=False)
    def frontend_index():
        return FileResponse(_index, media_type='text/html')

    @app.get('/{path:path}', include_in_schema=False)
    def frontend_route(path: str):
        if path.startswith(('api/', 'healthz')):
            return JSONResponse(status_code=404, content={'detail': 'Not found.'})
        candidate = (_dist / path).resolve()
        if _dist in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_index, media_type='text/html')
