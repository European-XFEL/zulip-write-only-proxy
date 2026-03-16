# syntax=docker/dockerfile:1
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV \
  PYTHONOPTIMIZE=2 \
  UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_CACHE_DIR=/opt/uv-cache/

COPY pyproject.toml uv.lock .python-version ./
COPY packages/zwop-contracts/pyproject.toml ./packages/zwop-contracts/pyproject.toml
COPY packages/zwop-service/pyproject.toml ./packages/zwop-service/pyproject.toml
COPY packages/zwop-token-writer/pyproject.toml ./packages/zwop-token-writer/pyproject.toml

RUN --mount=type=cache,target=/opt/uv-cache/ \
  uv sync --frozen --no-install-workspace --no-dev

COPY packages ./packages

RUN --mount=type=cache,target=/opt/uv-cache/ \
  uv sync --locked --package zwop-token-writer --no-dev

EXPOSE 8443

CMD ["uv", "run", "--package", "zwop-token-writer", "zwop-token-writer"]
