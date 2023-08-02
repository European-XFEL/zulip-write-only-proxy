from __future__ import annotations

import secrets
from typing import IO, Any, Union

import zulip
from pydantic import BaseModel, PrivateAttr, field_validator
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

    def list_topics(self):
        stream = self._client.get_stream_id(self.stream)
        if stream["result"] != "success":
            raise RuntimeError(
                f"Failed to get stream id for {self.stream}. Is bot added to stream?\n"
                f"Response was {stream}"
            )
        stream_id = stream["stream_id"]
        return self._client.get_stream_topics(stream_id)

    def send_message(self, topic: str, content: str):
        request = {
            "type": "stream",
            "to": self.stream,
            "topic": topic,
            "content": content,
        }

        return self._client.send_message(request)


class AdminClient(BaseModel):
    key: str
    admin: bool

    @classmethod
    def create(cls) -> Self:
        return cls(key=secrets.token_urlsafe(), admin=True)

    @field_validator("admin")
    def check_admin(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Admin client must be admin")
        return v


Client = Union[ScopedClient, AdminClient]
