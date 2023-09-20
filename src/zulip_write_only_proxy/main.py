from contextlib import asynccontextmanager
from tempfile import SpooledTemporaryFile
from typing import Annotated, Union

import fastapi
from fastapi.security import APIKeyHeader

from . import models, services


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    services.setup()
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
    content: Annotated[str, fastapi.Query(...)],
    image: Annotated[Union[fastapi.UploadFile, None], fastapi.File()] = None,
):
    if image:
        # Some screwing around to get the spooled tmp file to act more like a real file
        # since Zulip needs it to have a filename
        f: SpooledTemporaryFile = image.file  # type: ignore[assignment]
        f._file.name = image.filename  # type: ignore[attr-defined]

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
    topic: Annotated[str, fastapi.Query(...)],
    propagate_mode: Annotated[models.PropagateMode, fastapi.Query(...)],
    content: Annotated[str, fastapi.Query(...)],
):
    return client.update_message(message_id, topic, propagate_mode, content)


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
    f._file.name = file.filename  # type: ignore[attr-defined]

    return client.upload_file(f)


_docs_url = "https://zulip.com/api/get-stream-topics#response"


@app.get(
    "/get_topics",
    tags=["User"],
    response_description=f"See <a href='{_docs_url}'>{_docs_url}</a>",
)
def get_topics(
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
):
    try:
        return client.list_topics()
    except RuntimeError as e:
        raise fastapi.HTTPException(status_code=400, detail=str(e)) from e


@app.get("/me", tags=["User"])
def get_me(
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
) -> models.ScopedClient:
    return client


@app.get("/health")
def healthcheck():
    return "OK"


@app.post("/create_client", tags=["Admin"])
def create_client(
    admin_client: Annotated[models.AdminClient, fastapi.Depends(get_client)],
    proposal_no: Annotated[int, fastapi.Query(...)],
    stream: Annotated[Union[str, None], fastapi.Query()] = None,
):
    try:
        return services.create_client(proposal_no, stream)
    except ValueError as e:
        raise fastapi.HTTPException(status_code=400, detail=str(e)) from e
