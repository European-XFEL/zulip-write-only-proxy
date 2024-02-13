FROM node:21-slim AS frontend
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app/src/zulip_write_only_proxy/frontend

COPY ./src/zulip_write_only_proxy/frontend/package.json \
  ./src/zulip_write_only_proxy/frontend/pnpm-lock.yaml \
  /app/src/zulip_write_only_proxy/frontend

RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

COPY ./src/zulip_write_only_proxy/frontend/**.html \
  ./src/zulip_write_only_proxy/frontend/**.css \
  /app/src/zulip_write_only_proxy/frontend

RUN pnpm exec tailwindcss -i ./input.css -o ./static/main.css && \
  cp ./node_modules/htmx.org/dist/htmx.min.js ./static/htmx.min.js

FROM python:3.11

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache \
  python3 -m pip install --upgrade poetry pip && \
  poetry config virtualenvs.create false --local

COPY ./poetry.lock ./pyproject.toml ./README.md /app
COPY --link --from=frontend /app/src/zulip_write_only_proxy/frontend/static /app/src/zulip_write_only_proxy/frontend/static

RUN --mount=type=cache,target=/root/.cache \
  poetry install --no-root

COPY --link ./src /app/src

RUN --mount=type=cache,target=/root/.cache poetry install

EXPOSE 8000

HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1
