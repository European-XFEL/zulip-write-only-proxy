import secrets
from typing import IO, Any, Self

import zulip
from pydantic import BaseModel, Field


class ScopedClient(BaseModel):
    token: str
    proposal_no: int
    stream: str
    topic: str

    _client: zulip.Client = Field(
        init_var=None, default=None
    )  # Injected by service.setup

    @classmethod
    def create(cls, proposal_no: int) -> Self:
        return cls(
            token=secrets.token_urlsafe(),
            proposal_no=proposal_no,
            stream=f"some-pattern-{proposal_no}",
            topic=f"some-pattern-{proposal_no}",
        )

    def upload_image(self, image: IO[Any]):
        return self._client.upload_file(image)

    def send_message(self, content: str):
        request = {
            "type": "stream",
            "to": self.stream,
            "topic": self.topic,
            "content": content,
        }

        return self._client.send_message(request)
