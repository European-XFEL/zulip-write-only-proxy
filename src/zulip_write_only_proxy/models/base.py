import datetime
from abc import ABC

from pydantic import BaseModel


class Base(ABC, BaseModel):
    created_at: datetime.datetime

    @property
    def _key(self):  # pragma: no cover
        raise NotImplementedError
