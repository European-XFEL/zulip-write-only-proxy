# syntax=docker/dockerfile:1

## Frontend
FROM node:21-slim AS frontend
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app

COPY --link ./package.json ./pnpm-lock.yaml ./tailwind.config.js ./

RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

COPY ./packages/zwop-service/src/zwop/frontend/templates/ \
  ./packages/zwop-service/src/zwop/frontend/templates/

RUN pnpm build

ADD --link https://unpkg.com/htmx.org@1.9.10/dist/htmx.js \
  https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js \
  ./packages/zwop-service/src/zwop/frontend/static/


## Server
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV \
  PYTHONOPTIMIZE=2 \
  UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_CACHE_DIR=/opt/uv-cache/

RUN apt update && apt install -y openssh-client wget git && rm -rf /var/lib/apt/lists/*

COPY --link ./pyproject.toml ./uv.lock ./.python-version /app/
COPY --link ./packages/zwop-contracts/pyproject.toml /app/packages/zwop-contracts/pyproject.toml
COPY --link ./packages/zwop-service/pyproject.toml /app/packages/zwop-service/pyproject.toml
COPY --link ./packages/zwop-token-writer/pyproject.toml /app/packages/zwop-token-writer/pyproject.toml

RUN --mount=type=cache,target=/opt/uv-cache/ \
  uv sync --frozen --no-install-workspace --no-dev

COPY --link README.md ./
COPY --link packages ./packages

RUN --mount=type=cache,target=/opt/uv-cache/ \
    --mount=type=bind,source=.git,target=/app/.git \
  uv sync --locked --package zwop-service --no-dev

COPY --link --from=frontend /app/packages/zwop-service/src/zwop/frontend \
  /app/packages/zwop-service/src/zwop/frontend

EXPOSE 8000

ENV ZWOP_ADDRESS=http://0.0.0.0:8000

CMD ["uv", "run", "--package", "zwop-service", "-m", "zwop.main"]

HEALTHCHECK --start-interval=1s --start-period=30s --interval=60s \
  CMD wget http://0.0.0.0:8000/api/health || exit 1
