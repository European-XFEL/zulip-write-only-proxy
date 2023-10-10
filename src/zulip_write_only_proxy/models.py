from __future__ import annotations

import enum
import logging
import secrets
from typing import IO, Any, Union

import zulip
from pydantic import BaseModel, PrivateAttr, SecretStr, field_validator
from typing_extensions import Self

log = logging.getLogger(__name__)


class PropagateMode(str, enum.Enum):
    change_one = "change_one"
    change_all = "change_all"
    change_later = "change_later"


class ScopedClient(BaseModel):
    key: SecretStr

    proposal_no: int
    stream: str

    _client: zulip.Client = PrivateAttr()

    @classmethod
    def create(
        cls,
        proposal_no: int,
        stream: str | None = None,
    ) -> Self:
        self = cls(
            key=SecretStr(secrets.token_urlsafe()),
            proposal_no=proposal_no,
            stream=stream or f"some-pattern-{proposal_no}",
        )

        self._client.add_subscriptions(streams=[{"name": self.stream}])

        return self

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
        message_id: int,
        topic: str,
        propagate_mode: PropagateMode,
        content: str,
    ):
        request = {
            "message_id": message_id,
            "topic": topic,
            "propagate_mode": propagate_mode.value,
            "content": content,
        }

        return self._client.update_message(request)


class AdminClient(BaseModel):
    key: SecretStr
    admin: bool

    @classmethod
    def create(cls) -> Self:
        return cls(key=SecretStr(secrets.token_urlsafe()), admin=True)

    @field_validator("admin")
    def check_admin(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Admin client must be admin")
        return v


Client = Union[ScopedClient, AdminClient]
