# syntax=docker/dockerfile:1
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV \
  PYTHONOPTIMIZE=2 \
  UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_CACHE_DIR=/opt/uv-cache/

RUN apt update && apt install -y wget git && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock .python-version ./
COPY packages/zwop-contracts/pyproject.toml ./packages/zwop-contracts/pyproject.toml
COPY packages/zwop-service/pyproject.toml ./packages/zwop-service/pyproject.toml
COPY packages/zwop-token-writer/pyproject.toml ./packages/zwop-token-writer/pyproject.toml

RUN --mount=type=cache,target=/opt/uv-cache/ \
  uv sync --frozen --no-install-workspace --no-dev

COPY README.md ./
COPY packages ./packages

RUN --mount=type=cache,target=/opt/uv-cache/ \
    --mount=type=bind,source=.git,target=/app/.git \
  uv sync --locked --package zwop-service --no-dev

EXPOSE 8000

ENV ZWOP_ADDRESS=http://0.0.0.0:8000

CMD ["uv", "run", "--package", "zwop-service", "-m", "zwop.main"]
