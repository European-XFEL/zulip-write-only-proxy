import datetime
from abc import ABC

from pydantic import BaseModel, Field


class Base(ABC, BaseModel):
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
