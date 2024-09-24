import datetime
import secrets
from typing import IO, TYPE_CHECKING, Any

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    PrivateAttr,
    SecretStr,
    field_validator,
)

from .. import logger
from ..exceptions import ZwopException
from .base import Base
from .zulip import PropagateMode

if TYPE_CHECKING:
    import zulip


class NoBotForClientError(ZwopException):
    def __init__(self):
        super().__init__(status_code=404, detail="No Zulip bot configured for client")


class NoStreamForClientError(ZwopException):
    def __init__(self):
        super().__init__(
            status_code=404, detail="No Zulip stream configured for client"
        )


class ScopedClientCreate(BaseModel):
    proposal_no: int
    stream: str | None = None
    bot_site: str = "https://mylog.connect.xfel.eu/"
    bot_id: int | None = None

    token: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe()), init_var=False
    )

    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now, init_var=False
    )


class ScopedClient(Base):
    proposal_no: int
    proposal_id: int
    stream: str | None  # type: ignore [reportIncompatibleVariableOverride]
    bot_id: int | None
    bot_site: HttpUrl | None
    token: SecretStr

    # created_at - from base
    created_by: str

    _client: "zulip.Client" = PrivateAttr()

    @property
    def _key(self):
        if not self.bot_site:
            return f"{self.proposal_no}/{self.created_by}"
        return f"{self.proposal_no}/{self.created_by}/{self.bot_site.host}"

    @property
    def _bot_key(self) -> str:
        if not self.bot_site or not self.bot_id:
            raise NoBotForClientError

        return f"{self.bot_site.host}/{self.bot_id}"

    def upload_file(self, file: IO[Any]):
        return self._client.upload_file(file)

    def get_stream_topics(self):
        if self.stream is None:
            raise NoStreamForClientError

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
        # messages to fetch. TODO: handle multi-page results for more than 100 messages
        messages = self._client.get_messages(request)
        messages["messages"] = sorted(
            messages["messages"], key=lambda m: m["id"], reverse=True
        )
        return messages

    def get_me(self):
        return self._client.get_profile()


class ScopedClientWithToken(ScopedClient):
    token: str  # type: ignore[assignment]

    @field_validator("token")
    @classmethod
    def _set_token(cls, v: str | SecretStr) -> str:
        return v.get_secret_value() if isinstance(v, SecretStr) else v
