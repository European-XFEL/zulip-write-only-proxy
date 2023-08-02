from __future__ import annotations

import secrets
from typing import IO, Any

import zulip
from pydantic import BaseModel, PrivateAttr
from typing_extensions import Self


class ScopedClient(BaseModel):
    key: str

    proposal_no: int
    stream: str

    _client: zulip.Client = PrivateAttr()

    @classmethod
    def create(
        cls,
        proposal_no: int,
        stream: str | None = None,
    ) -> Self:
        return cls(
            key=secrets.token_urlsafe(),
            proposal_no=proposal_no,
            stream=stream or f"some-pattern-{proposal_no}",
        )

    def upload_image(self, image: IO[Any]):
        return self._client.upload_file(image)

    def send_message(self, topic: str, content: str):
        request = {
            "type": "stream",
            "to": self.stream,
            "topic": topic,
            "content": content,
        }

        return self._client.send_message(request)
