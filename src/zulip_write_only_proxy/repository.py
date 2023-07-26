from pathlib import Path

import orjson
from pydantic import BaseModel, field_validator

from .model import ScopedClient


class JSONRepository(BaseModel):
    """A basic file/JSON-based repository for storing client entries."""

    path: Path

    def get(self, token: str) -> ScopedClient:
        with self.path.open("rb") as f:
            data = orjson.loads(f.read())
            return ScopedClient(token=token, **data[token])

    def put(self, proposal: ScopedClient) -> None:
        with self.path.open("rb") as f:
            data = orjson.loads(f.read())
            if proposal.proposal_no in data.values():
                raise ValueError("Client already exists")

            data[proposal.token] = proposal.model_dump(exclude={"token"})

        with self.path.open("wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    def list(self):
        with self.path.open("rb") as f:
            data = orjson.loads(f.read())
            return [ScopedClient(token=token, **entry) for entry, token in data.items()]

    @field_validator("path")
    @classmethod
    def check_path(cls, v: Path) -> Path:
        if not v.exists():
            v.touch()
            v.write_text("{}")
        return v
