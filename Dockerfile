# syntax=docker/dockerfile:1

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

FROM python:3.12-alpine AS prod

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONOPTIMIZE 2

WORKDIR /app

RUN apk update && apk add --no-cache openssh

RUN --mount=type=cache,target=/root/.cache \
  python3 -m pip install --upgrade poetry pip && \
  poetry config virtualenvs.create false --local

COPY ./poetry.lock ./pyproject.toml ./README.md /app/

RUN --mount=type=cache,target=/root/.cache \
  poetry install --no-root

COPY --link ./src /app/src

RUN --mount=type=cache,target=/root/.cache poetry install

COPY --link --from=frontend /app/src/zulip_write_only_proxy/frontend/static \
  /app/src/zulip_write_only_proxy/frontend/static

EXPOSE 8000

ENV ZWOP_ADDRESS=http://0.0.0.0:8000

CMD ["poe", "up"]

HEALTHCHECK --start-interval=1s --start-period=30s --interval=60s \
  CMD wget --spider http://0.0.0.0:8000/api/health || exit 1

FROM prod AS dev

RUN --mount=type=cache,target=/root/.cache \
  python3 -m pip install debugpy

EXPOSE 5678

CMD ["python3", "-Xfrozen_modules=off", "-m", "debugpy", "--listen", "0.0.0.0:5678", "-m", "zulip_write_only_proxy.main"]
