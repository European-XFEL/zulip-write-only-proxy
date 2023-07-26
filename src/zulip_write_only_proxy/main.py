from contextlib import asynccontextmanager

import fastapi
import uvicorn
import zulip

from . import zulip_client


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    zulip_client.setup()
    yield


app = fastapi.FastAPI(title="Zulip Write Only Proxy", lifespan=lifespan)


@app.post("/message")
def post_message(
    stream: str,
    topic: str,
    content: str,
    client: zulip.Client = fastapi.Depends(zulip_client.get_client),
):
    request = {
        "type": "stream",
        "to": stream,
        "topic": topic,
        "content": content,
    }
    return client.send_message(request)


if __name__ == "__main__":
    uvicorn.run(
        "zulip_write_only_proxy.main:app",
    )
