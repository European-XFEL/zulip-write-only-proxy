import enum
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, HttpUrl, SecretStr

from .base import Base


class PropagateMode(str, enum.Enum):
    change_one = "change_one"
    change_all = "change_all"
    change_later = "change_later"


class BotConfig(Base):
    email: EmailStr
    key: SecretStr
    site: Annotated[HttpUrl, Field(default="https://mylog.connect.xfel.eu/")]
    id: int
    proposal_no: int

    # created at is optional for bots, not that important/used
    created_at: datetime | None = None  # type: ignore[assignment]

    @property
    def _key(self):
        return f"{self.site.host}/{self.id}"


MessageID = int


class Message(BaseModel):
    topic: str
    id: MessageID
    content: str
    timestamp: datetime


class Messages(BaseModel):
    found_newest: bool
    found_oldest: bool
    messages: list[Message]
    client: str
