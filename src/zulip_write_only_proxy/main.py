from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from tempfile import SpooledTemporaryFile
from typing import Annotated, Union

import fastapi
from fastapi.security import APIKeyHeader

from . import __version__, __version_tuple__, _logging, models, services


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    services.setup()
    logging.getLogger("uvicorn.access").addFilter(_logging.EndpointFilter())
    yield


app = fastapi.FastAPI(title="Zulip Write Only Proxy", lifespan=lifespan)

api_key_header = APIKeyHeader(name="X-API-key")


def get_client(key: Annotated[str, fastapi.Security(api_key_header)]) -> models.Client:
    try:
        return services.get_client(key)
    except KeyError as e:
        raise fastapi.HTTPException(status_code=401, detail="Unauthorised") from e


_docs_url = "https://zulip.com/api/send-message#response"


@app.post(
    "/send_message",
    tags=["User"],
    response_description=f"See <a href='{_docs_url}'>{_docs_url}</a>",
)
def send_message(
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
    topic: Annotated[str, fastapi.Query(...)],
    content: Annotated[str, fastapi.Body(...)],
    image: Annotated[Union[fastapi.UploadFile, None], fastapi.File()] = None,
):
    if image:
        # Some screwing around to get the spooled tmp file to act more like a real file
        # since Zulip needs it to have a filename
        f: SpooledTemporaryFile = image.file  # type: ignore[assignment]
        f._file.name = image.filename  # type: ignore[misc, assignment]

        result = client.upload_file(f)

        content += f"\n[]({result['uri']})"

    return client.send_message(topic, content)


_docs_url = "https://zulip.com/api/update-message#response"


@app.patch(
    "/update_message",
    tags=["User"],
    response_description=f"See <a href='{_docs_url}'>{_docs_url}</a>",
)
def update_message(
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
    message_id: Annotated[int, fastapi.Query(...)],
    propagate_mode: Annotated[models.PropagateMode, fastapi.Query(...)],
    content: Annotated[str | None, fastapi.Body(media_type="text/plain")] = None,
    topic: Annotated[str | None, fastapi.Query()] = None,
):
    if content or topic:
        return client.update_message(topic, content, message_id, propagate_mode)
    else:
        raise fastapi.HTTPException(
            status_code=400,
            detail=(
                "Either content (update message text) or topic (rename message topic) "
                "must be provided"
            ),
        )


_docs_url = "https://zulip.com/api/upload-file#response"


@app.post(
    "/upload_file",
    tags=["User"],
    response_description=f"See <a href='{_docs_url}'>{_docs_url}</a>",
)
def upload_file(
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
    file: Annotated[fastapi.UploadFile, fastapi.File(...)],
):
    f: SpooledTemporaryFile = file.file  # type: ignore[assignment]
    f._file.name = file.filename  # type: ignore[misc, assignment]

    return client.upload_file(f)


_docs_url = "https://zulip.com/api/get-stream-topics#response"


@app.get(
    "/get_stream_topics",
    tags=["User"],
    response_description=f"See <a href='{_docs_url}'>{_docs_url}</a>",
)
def get_stream_topics(
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
):
    return client.get_stream_topics()


@app.get("/me", tags=["User"], response_model_exclude={"key"})
def get_me(
    client: Annotated[models.Client, fastapi.Depends(get_client)]
) -> models.Client:
    return client


@app.get("/health", tags=["Admin"])
def healthcheck():
    return {
        "status": "OK",
        "dirty": "dirty" in __version__,
        "dev": "+" in __version__,
        "version": __version__,
        "version_tuple": __version_tuple__,
    }


@app.post("/create_client", tags=["Admin"])
def create_client(
    admin_client: Annotated[models.AdminClient, fastapi.Depends(get_client)],
    client: Annotated[models.ScopedClient, fastapi.Depends(services.create_client)],
) -> models.ScopedClientWithKey:
    try:
        dump = client.model_dump()
        dump["key"] = client.key.get_secret_value()
        return models.ScopedClientWithKey(**dump)
    except ValueError as e:
        raise fastapi.HTTPException(status_code=400, detail=str(e)) from e
