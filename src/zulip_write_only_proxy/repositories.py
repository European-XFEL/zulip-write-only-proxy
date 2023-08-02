import threading
from pathlib import Path

import orjson
from pydantic import BaseModel, field_validator

from . import models

file_lock = threading.Lock()


class JSONRepository(BaseModel):
    """A basic file/JSON-based repository for storing client entries."""

    path: Path

    def get(self, key: str) -> models.Client:
        with self.path.open("rb") as f:
            data = orjson.loads(f.read())
            client_data = data[key]

            if client_data.get("admin"):
                return models.AdminClient(key=key, **client_data)

            return models.ScopedClient(key=key, **client_data)

    def put(self, client: models.ScopedClient) -> None:
        with file_lock:
            with self.path.open("rb") as f:
                data = orjson.loads(f.read())
                proposal_nos = [value.get("proposal_no") for value in data.values()]
                if client.proposal_no in proposal_nos:
                    reversed_data = {
                        value.get("proposal_no"): {"key": key, **value}
                        for key, value in data.items()
                    }

                    raise ValueError(
                        f"Client already exists for {client.proposal_no=}: "
                        f"{reversed_data[client.proposal_no]}"
                    )

                data[client.key] = client.model_dump(exclude={"key"})

            with self.path.open("wb") as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    def put_admin(self, client: models.AdminClient) -> None:
        with file_lock:
            with self.path.open("rb") as f:
                data = orjson.loads(f.read())
                data[client.key] = client.model_dump(exclude={"key"})

            with self.path.open("wb") as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    def list(self):
        with self.path.open("rb") as f:
            data = orjson.loads(f.read())
            return [models.ScopedClient(key=key, **value) for key, value in data.items()]

    @field_validator("path")
    @classmethod
    def check_path(cls, v: Path) -> Path:
        if not v.exists():
            v.touch()
            v.write_text("{}")
        return v
