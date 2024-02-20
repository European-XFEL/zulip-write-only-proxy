import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, TypeVar

import orjson
import pydantic
from anyio import Path as APath
from pydantic import BaseModel

from . import logger

T = TypeVar("T", bound=BaseModel)


@dataclass
class BaseRepository(Generic[T]):
    file: Path
    index: str
    model: T

    lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    data: dict[str, T] = field(default_factory=dict, init=False, repr=False)

    @staticmethod
    def _serialize_pydantic(obj):
        if type(obj) is pydantic.AnyUrl:
            return str(obj)
        if type(obj) is pydantic.SecretStr:
            return obj.get_secret_value()
        raise TypeError

    async def load(self):
        async with self.lock:
            if not await APath(self.file).exists():
                return

            self.data = orjson.loads(await APath(self.file).read_bytes())

    async def write(self):
        async with self.lock:
            await APath(self.file).write_bytes(
                orjson.dumps(
                    self.data,
                    option=orjson.OPT_INDENT_2,
                    default=self._serialize_pydantic,
                )
            )

    async def get(self, key: str) -> T:
        try:
            return self.model.model_validate(self.data[key])
        except KeyError:
            logger.debug("Key not found, reload from file")
            await self.load()
            return self.model.model_validate(self.data[key])

    async def insert(self, item: T):
        _item = item.model_dump()
        key = _item[self.index]

        if type(key) is pydantic.SecretStr:
            key = key.get_secret_value()

        self.data[key] = _item

        await self.write()

    async def list(self) -> list[T]:
        return [self.model.model_validate(item) for item in self.data.values()]
