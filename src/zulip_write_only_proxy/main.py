from contextlib import asynccontextmanager
from tempfile import SpooledTemporaryFile
from typing import Union

import fastapi
import uvicorn
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from . import model, service


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    service.setup()
    yield


app = fastapi.FastAPI(title="Zulip Write Only Proxy", lifespan=lifespan)

api_key_header = APIKeyHeader(name="X-API-key")


def get_client(key: str = fastapi.Security(api_key_header)) -> model.Client:
    try:
        return service.get_client(key)
    except KeyError as e:
        raise fastapi.HTTPException(status_code=404, detail="Key not found") from e


send_msg_docs_url = "https://zulip.com/api/send-message#response"


@app.post(
    "/message",
    tags=["User"],
    response_description=f"See <a href='{send_msg_docs_url}'>{send_msg_docs_url}</a>",
)
def send_message(
    client: model.ScopedClient = fastapi.Depends(get_client),
    topic: str = fastapi.Query(...),
    content: str = fastapi.Query(...),
    image: fastapi.UploadFile = fastapi.File(None),
):
    if image:
        # Some screwing around to get the spooled tmp file to act more like a real file
        # since Zulip needs it to have a filename
        f: SpooledTemporaryFile = image.file  # type: ignore
        f._file.name = image.filename  # type: ignore

        result = client.upload_image(f)

        content += f"\n[]({result['uri']})"

    return client.send_message(topic, content)


# This should not be here
class UploadImageResponse(BaseModel):
    uri: str
    msg: str
    result: str = "success"


upload_f_docs_url = "https://zulip.com/api/upload-file#response"


@app.post(
    "/upload_image",
    tags=["User"],
    response_description=f"See <a href='{upload_f_docs_url}'>{upload_f_docs_url}</a>",
)
def upload_image(
    client: model.ScopedClient = fastapi.Depends(get_client),
    image: fastapi.UploadFile = fastapi.File(...),
):
    f: SpooledTemporaryFile = image.file  # type: ignore
    f._file.name = image.filename  # type: ignore

    return client.upload_image(f)


@app.post("/create_client", tags=["Admin"])
def create_client(
    admin_client: model.AdminClient = fastapi.Depends(get_client),
    proposal_no: int = fastapi.Query(...),
    stream: Union[str, None] = fastapi.Query(None),
):
    try:
        return service.create_client(proposal_no, stream)
    except ValueError as e:
        raise fastapi.HTTPException(status_code=400, detail=str(e)) from e


if __name__ == "__main__":
    uvicorn.run(app="zulip_write_only_proxy.main:app")
