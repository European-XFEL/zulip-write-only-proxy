FROM python:3.11

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache \
    python3 -m pip install --upgrade poetry pip

COPY ./poetry.lock ./pyproject.toml ./README.md /app
COPY ./src /app/src

RUN poetry config virtualenvs.create false --local

RUN --mount=type=cache,target=/root/.cache\
    poetry install

CMD ["uvicorn", "zulip_write_only_proxy.main:app", "--host", "0.0.0.0", "--port", "8000"]

HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1
