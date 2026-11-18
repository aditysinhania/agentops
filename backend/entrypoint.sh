#!/bin/sh
set -eu
cd /app/backend
alembic -c alembic.ini upgrade head
exec uvicorn agentops_api.main:app --host 0.0.0.0 --port "${PORT:-3000}" --proxy-headers
