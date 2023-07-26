from contextlib import asynccontextmanager
from tempfile import SpooledTemporaryFile

import fastapi
import uvicorn
from fastapi.security import APIKeyHeader

from . import service


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    service.setup()
    yield


app = fastapi.FastAPI(title="Zulip Write Only Proxy", lifespan=lifespan)

api_key_header = APIKeyHeader(name="X-API-key")


def get_client(key: str = fastapi.Security(api_key_header)) -> service.ScopedClient:
    try:
        return service.get_client(key)
    except KeyError as e:
        raise fastapi.HTTPException(status_code=404, detail="Key not found") from e


@app.post("/message", tags=["User"])
def send_message(
    client=fastapi.Depends(get_client),
    content: str = fastapi.Query(...),
    image: fastapi.UploadFile = fastapi.File(None),
):
    if image:
        # Some screwing around to get the spooled tmp file to act more like a real file
        # since Zulip needs it to have a filename
        f: SpooledTemporaryFile = image.file  # type: ignore
        f._file.name = image.filename  # type: ignore

        result = client.upload_image(f)

        content += f" []({result['uri']})"

    return client.send_message(content)


if __name__ == "__main__":
    uvicorn.run(app="zulip_write_only_proxy.main:app")
