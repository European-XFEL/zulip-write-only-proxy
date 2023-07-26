import secrets
from typing import IO, Any, Self

import zulip
from pydantic import BaseModel


class ScopedClient(BaseModel):
    key: str

    proposal_no: int
    stream: str
    topic: str

    _client: zulip.Client = None  # type: ignore

    @classmethod
    def create(
        cls,
        proposal_no: int,
        stream: str | None = None,
        topic: str | None = None,
    ) -> Self:
        return cls(
            key=secrets.token_urlsafe(),
            proposal_no=proposal_no,
            stream=stream or f"some-pattern-{proposal_no}",
            topic=topic or f"some-pattern-{proposal_no}",
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
