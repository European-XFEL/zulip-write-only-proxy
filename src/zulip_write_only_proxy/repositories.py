import threading
from pathlib import Path

import orjson
from pydantic import BaseModel, SecretStr, field_validator

from . import models

file_lock = threading.Lock()


class JSONRepository(BaseModel):
    """A basic file/JSON-based repository for storing client entries."""

    path: Path

    def get(self, key: str) -> models.Client:
        data = orjson.loads(self.path.read_bytes())
        client_data = data[key]

        if client_data.get("admin"):
            return models.AdminClient(key=SecretStr(key), **client_data)

        return models.ScopedClient(key=SecretStr(key), **client_data)

    def put(self, client: models.Client) -> None:
        with file_lock:
            data: dict[str, dict] = orjson.loads(self.path.read_bytes())
            data[client.key.get_secret_value()] = client.model_dump(exclude={"key"})
            self.path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    def list(self) -> list[models.Client]:
        data = orjson.loads(self.path.read_bytes())

        clients = [
            models.ScopedClient(key=key, **value)
            for key, value in data.items()
            if not value.get("admin")
        ]

        admins = [
            models.AdminClient(key=key, **value)
            for key, value in data.items()
            if value.get("admin")
        ]

        return clients + admins

    @field_validator("path")
    @classmethod
    def check_path(cls, v: Path) -> Path:
        if not v.exists():
            v.touch()
            v.write_text("{}")
        return v
