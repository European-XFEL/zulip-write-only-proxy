import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, TypeVar

import orjson
import pydantic
from anyio import Path as APath

from . import logger
from .models.base import Base

T = TypeVar("T", bound=Base)


@dataclass
class BaseRepository(Generic[T]):
    file: Path
    model: type[T]

    lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    data: dict[str, T] = field(default_factory=dict, init=False, repr=False)

    _data: list[T] = field(default_factory=list, init=False, repr=False)

    @staticmethod
    def _serialize_pydantic(obj):
        if type(obj) is pydantic.AnyUrl:
            return str(obj)
        if type(obj) is pydantic.SecretStr:
            return obj.get_secret_value()
        if issubclass(obj.__class__, Base):
            return obj.model_dump()
        raise TypeError

    async def load(self):
        async with self.lock:
            if not await APath(self.file).exists():
                return

            self._data = [
                self.model.model_validate(item)
                for item in orjson.loads(await APath(self.file).read_bytes())
            ]

            self.data = {item._key: item for item in self._data}

    async def write(self):
        async with self.lock:
            await APath(self.file).write_bytes(
                orjson.dumps(
                    self._data,
                    option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
                    default=self._serialize_pydantic,
                )
            )

    def _get_key_value(self, item, by):
        k = getattr(item, by, None)
        if isinstance(k, pydantic.SecretStr):
            k = k.get_secret_value()
        return k

    def _get_by(self, by, key):
        return next(
            (item for item in self._data if self._get_key_value(item, by) == key),
            None,
        )

    async def get(self, key: str | int, by: str | None = None) -> T | None:
        res = self._get_by(by, key) if by else self.data.get(str(key))

        if res is None:
            logger.warning("Key not found", key=key, by=by)

        return res

    async def delete(self, key: str, by: str | None = None) -> str:
        item = self._get_by(by, key) if by else self.data.get(key)

        if item is None:
            raise KeyError(by or "key", key)

        _key = item._key

        self._data.remove(item)
        del self.data[_key]

        await self.write()

        return _key

    async def insert(self, item: T):
        if item._key in self.data:
            msg = "Key already exists"
            logger.warning(msg, key=item._key)
            raise ValueError(msg)

        self._data.append(item)
        self.data[item._key] = self._data[-1]

        await self.write()

    async def list(self) -> list[T]:
        return self._data
