FROM python:3.11

WORKDIR /app

RUN python3 -m pip install --upgrade poetry pip

COPY ./poetry.lock ./pyproject.toml ./README.md /app
COPY ./src /app/src

RUN poetry config virtualenvs.create false --local
RUN poetry install

CMD ["uvicorn", "zulip_write_only_proxy.main:app", "--host", "0.0.0.0", "--port", "8000"]
