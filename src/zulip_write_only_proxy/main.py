from contextlib import asynccontextmanager
from tempfile import SpooledTemporaryFile

import fastapi
import uvicorn

from . import service


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    service.setup()
    yield


app = fastapi.FastAPI(title="Zulip Write Only Proxy", lifespan=lifespan)


@app.post("/message")
def send_message(
    client: service.ScopedClient = fastapi.Depends(service.get_proposal),
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
    uvicorn.run("zulip_write_only_proxy.main:app")
