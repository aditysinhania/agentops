FROM node:22-alpine AS frontend-build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@11.25.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig*.json vite.config.ts tailwind.config.js postcss.config.js index.html ./
COPY frontend ./frontend
COPY public ./public
RUN pnpm install --frozen-lockfile && pnpm build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend:/app/sdk FRONTEND_DIST=/app/frontend/dist
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
COPY sdk /app/sdk
RUN pip install --no-cache-dir --no-deps /app/sdk
COPY --from=frontend-build /app/dist /app/frontend/dist
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && useradd --create-home --uid 10001 agentops && chown -R agentops:agentops /app
USER agentops
EXPOSE 3000
CMD ["/app/entrypoint.sh"]
