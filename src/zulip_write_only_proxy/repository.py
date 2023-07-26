from pathlib import Path
from pydantic import BaseModel, field_validator

import orjson
from .model import Proposal


class ProposalRepository(BaseModel):
    """A basic file/JSON-based repository for storing proposal entries."""

    path: Path

    def get(self, token: str) -> Proposal:
        with self.path.open("rb") as f:
            data = orjson.loads(f.read())
            return Proposal(token=token, **data[token])

    def put(self, proposal: Proposal) -> None:
        with self.path.open("rb") as f:
            data = orjson.loads(f.read())
            if proposal.proposal_no in data.values():
                raise ValueError("Proposal already exists")

            data[proposal.token] = proposal.model_dump(exclude={"token"})

        with self.path.open("wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    def list(self):
        with self.path.open("rb") as f:
            data = orjson.loads(f.read())
            return [Proposal(token=token, **entry) for entry, token in data.items()]

    @field_validator("path")
    @classmethod
    def check_path(cls, v: Path) -> Path:
        if not v.exists():
            v.touch()
            v.write_text("{}")
        return v
