# Builds the Svelte/Vite client, then runs the FastAPI server with uv.

FROM node:26-alpine AS client-build
WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci --ignore-scripts
COPY client/ ./
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_PUBLISHABLE_KEY
ARG VITE_API_URL
ARG VITE_GA_ID
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_PUBLISHABLE_KEY=$VITE_SUPABASE_PUBLISHABLE_KEY
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_GA_ID=$VITE_GA_ID
RUN test -n "$VITE_SUPABASE_URL" && test -n "$VITE_SUPABASE_PUBLISHABLE_KEY"
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS server
WORKDIR /app/server

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --no-dev --frozen

COPY server/ ./
COPY --from=client-build /app/client/dist ./static
RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["/app/server/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
