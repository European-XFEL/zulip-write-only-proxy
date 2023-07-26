from contextlib import asynccontextmanager
from tempfile import SpooledTemporaryFile

import fastapi
import uvicorn
import zulip

from . import zulip_client, service


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    zulip_client.setup()
    yield


app = fastapi.FastAPI(title="Zulip Write Only Proxy", lifespan=lifespan)


@app.post("/message")
def post_message(
    proposal: service.Proposal = fastapi.Depends(service.get_proposal),
    content: str = fastapi.Query(...),
    client: zulip.Client = fastapi.Depends(zulip_client.get_client),
    image: fastapi.UploadFile = fastapi.File(None),
):
    if image:
        # Some screwing around to get the spooled tmp file to act more like a real file
        # since Zulip needs it to have a filename
        f: SpooledTemporaryFile = image.file  # type: ignore
        f._file.name = image.filename  # type: ignore

        result = client.upload_file(f)
        content += f" []({result['uri']})"

    request = {
        "type": "stream",
        "to": proposal.stream,
        "topic": proposal.topic,
        "content": content,
    }

    return client.send_message(request)


if __name__ == "__main__":
    uvicorn.run("zulip_write_only_proxy.main:app")
