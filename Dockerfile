# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV \
  PYTHONOPTIMIZE=2 \
  UV_CACHE_DIR=/opt/uv-cache/ \
  UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy

RUN apt update && \
  apt install -y wget --no-install-recommends && \
  rm -rf /var/lib/apt/lists/*


FROM base AS dev

ENV \
  PNPM_HOME="/pnpm" \
  PATH="/pnpm:$PATH"

RUN apt update && \
  apt install -y git node-corepack --no-install-recommends && \
  corepack enable && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --link ./pyproject.toml ./uv.lock ./.python-version /app/

RUN --mount=type=cache,target=/opt/uv-cache/ \
  uv sync --frozen --no-install-workspace

COPY --link README.md ./
COPY --link packages ./packages

RUN --mount=type=cache,id=pnpm,target=/pnpm/store cd packages/zwop \
  pnpm install --frozen-lockfile

RUN --mount=type=cache,target=/opt/uv-cache/ \
    --mount=type=bind,source=.git,target=/app/.git \
  uv sync --locked


FROM dev AS build

RUN --mount=type=cache,target=/opt/uv-cache/ \
    --mount=type=bind,source=.git,target=/app/.git \
  uv build --package zwop && \
  uv build --package zwop-tws


FROM base AS zwop-tws
RUN --mount=type=bind,from=build,source=/app/dist,target=/dist \
    --mount=type=cache,target=/opt/uv-cache/ \
  uv pip install --system /dist/zwop_tws-*.whl

CMD ["zwop-tws"]


FROM base AS zwop
RUN --mount=type=bind,from=build,source=/app/dist,target=/dist \
    --mount=type=cache,target=/opt/uv-cache/ \
  uv pip install --system /dist/zwop-*.whl /dist/zwop_tws-*.whl

CMD ["zwop"]


# Use dev as base so that default target is dev
FROM dev
