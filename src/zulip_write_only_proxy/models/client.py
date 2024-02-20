import datetime
import secrets
from typing import IO, TYPE_CHECKING, Any

from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    SecretStr,
    field_validator,
)

from .. import logger
from .zulip import PropagateMode

if TYPE_CHECKING:
    import zulip


class ScopedClientCreate(BaseModel):
    proposal_no: int
    stream: str | None = None
    bot_name: str | None = None
    bot_email: str | None = None
    bot_key: str | None = None
    bot_site: str = "https://mylog.connect.xfel.eu/"


class ScopedClient(BaseModel):
    proposal_no: int
    stream: str  # type: ignore [reportIncompatibleVariableOverride]
    bot_name: str
    bot_id: int
    key: SecretStr = Field(default_factory=lambda: SecretStr(secrets.token_urlsafe()))

    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    created_by: str

    _client: "zulip.Client" = PrivateAttr()

    def upload_file(self, file: IO[Any]):
        return self._client.upload_file(file)

    def get_stream_topics(self):
        stream = self._client.get_stream_id(self.stream)
        if stream["result"] != "success":
            logger.error(
                "Failed to get stream id",
                stream=self.stream,
                response=stream,
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
        propagate_mode: PropagateMode | None,
    ):
        request: dict[str, str | int] = {"message_id": message_id}

        if propagate_mode:
            request["propagate_mode"] = propagate_mode

        if topic:
            request["topic"] = topic

        if content:
            request["content"] = content

        return self._client.update_message(request)

    def get_messages(self):
        request = {
            "anchor": "newest",
            "num_before": 100,
            "num_after": 0,
            "apply_markdown": "false",
            "narrow": [
                {"operator": "sender", "operand": self.bot_id},
                {"operator": "stream", "operand": self.stream},
            ],
        }
        # result should be success, if found oldest and found newest both true no more
        # messages to fetch
        return self._client.get_messages(request)

    def get_me(self):
        return self._client.get_profile()


class ScopedClientWithKey(ScopedClient):
    key: str  # type: ignore[assignment]

    @field_validator("key")
    @classmethod
    def _set_key(cls, v: str | SecretStr) -> str:
        return v.get_secret_value() if isinstance(v, SecretStr) else v
