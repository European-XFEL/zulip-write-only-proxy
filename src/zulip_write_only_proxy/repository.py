from pathlib import Path

import orjson
from pydantic import BaseModel, field_validator

from .model import ScopedClient


class JSONRepository(BaseModel):
    """A basic file/JSON-based repository for storing client entries."""

    path: Path

    def get(self, key: str) -> ScopedClient:
        with self.path.open("rb") as f:
            data = orjson.loads(f.read())
            return ScopedClient(key=key, **data[key])

    def put(self, client: ScopedClient) -> None:
        with self.path.open("rb") as f:
            data = orjson.loads(f.read())
            proposal_nos = [value["proposal_no"] for value in data.values()]
            if client.proposal_no in proposal_nos:
                raise ValueError(f"Client already exists for {client.proposal_no=}")

            data[client.key] = client.model_dump(exclude={"key"})

        with self.path.open("wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    def list(self):
        with self.path.open("rb") as f:
            data = orjson.loads(f.read())
            return [ScopedClient(key=key, **value) for key, value in data.items()]

    @field_validator("path")
    @classmethod
    def check_path(cls, v: Path) -> Path:
        if not v.exists():
            v.touch()
            v.write_text("{}")
        return v
