from fastapi import APIRouter
from agentops_api.api.routes import agents, analytics, api_keys, auth, datasets, evaluations, prompts, settings, traces

api_router = APIRouter(prefix='/api')
for module in (auth, agents, traces, datasets, evaluations, prompts, api_keys, analytics, settings):
    api_router.include_router(module.router)
api_router.include_router(traces.telemetry_router)
