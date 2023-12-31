from __future__ import annotations

import enum
import logging
import secrets
from typing import IO, Any, Union

import zulip
from pydantic import BaseModel, Field, PrivateAttr, SecretStr, field_validator

log = logging.getLogger(__name__)


class PropagateMode(str, enum.Enum):
    change_one = "change_one"
    change_all = "change_all"
    change_later = "change_later"


class ScopedClientCreate(BaseModel):
    proposal_no: int
    stream: str | None


class ScopedClient(ScopedClientCreate):
    key: SecretStr = Field(default_factory=lambda: SecretStr(secrets.token_urlsafe()))

    proposal_no: int
    stream: str

    _client: zulip.Client = PrivateAttr()

    def upload_file(self, file: IO[Any]):
        return self._client.upload_file(file)

    def get_stream_topics(self):
        stream = self._client.get_stream_id(self.stream)
        if stream["result"] != "success":
            log.error(
                f"failed to get stream id for {self.stream}, "
                f"zulip api response: {stream}"
            )
            return stream
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

    def update_message(
        self,
        topic: str | None,
        content: str | None,
        message_id: int,
        propagate_mode: PropagateMode,
    ):
        request = {
            "message_id": message_id,
            "propagate_mode": propagate_mode.value,
        }

        if topic:
            request["topic"] = topic

        if content:
            request["content"] = content

        return self._client.update_message(request)


class ScopedClientWithKey(ScopedClient):
    key: str  # type: ignore[assignment]


class AdminClient(BaseModel):
    key: SecretStr = Field(default_factory=lambda: SecretStr(secrets.token_urlsafe()))
    admin: bool

    @field_validator("admin")
    def check_admin(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Admin client must be admin")
        return v


Client = Union[ScopedClient, AdminClient]
