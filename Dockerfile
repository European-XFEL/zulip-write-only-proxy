# syntax=docker/dockerfile:1

## Frontend
FROM node:21-slim AS frontend
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app

COPY --link ./package.json ./pnpm-lock.yaml ./tailwind.config.js ./

RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

COPY ./src/zulip_write_only_proxy/frontend/templates/ \
  ./src/zulip_write_only_proxy/frontend/templates/

RUN pnpm build

ADD --link https://unpkg.com/htmx.org@1.9.10/dist/htmx.js \
  https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js \
  ./src/zulip_write_only_proxy/frontend/static/


## Server
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV \
  PYTHONOPTIMIZE=2 \
  UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_CACHE_DIR=/opt/uv-cache/

RUN apt update && apt install -y openssh-client wget && rm -rf /var/lib/apt/lists/*

COPY --link ./pyproject.toml ./uv.lock /app/

RUN --mount=type=cache,target=/opt/uv-cache/ \
  uv sync --locked --no-install-project

COPY --link README.md src ./

RUN --mount=type=cache,target=/opt/uv-cache/ \
  uv sync --locked

COPY --link --from=frontend /app/src/zulip_write_only_proxy/frontend \
  /app/src/zulip_write_only_proxy/frontend

EXPOSE 8000

ENV ZWOP_ADDRESS=http://0.0.0.0:8000

CMD ["uv", "run", "-m", "zulip_write_only_proxy.main"]

HEALTHCHECK --start-interval=1s --start-period=30s --interval=60s \
  CMD wget --spider http://0.0.0.0:8000/api/health || exit 1
