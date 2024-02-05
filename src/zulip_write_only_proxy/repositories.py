import threading
from pathlib import Path

import orjson
import zulip
from pydantic import BaseModel, SecretStr, field_validator, validate_call

from . import models

file_lock = threading.Lock()


class ZuliprcRepository(BaseModel):
    directory: Path

    def get(self, key: str) -> zulip.Client:
        return zulip.Client(config_file=str(self.directory / f"{key}.zuliprc"))

    @validate_call
    def put(self, name: str, email: str, key: str, site: str) -> zulip.Client:
        (self.directory / f"{name}.zuliprc").write_text(
            f"""[api]
email={email}
key={key}
site={site}
"""
        )
        return zulip.Client(config_file=str(self.directory / f"{name}.zuliprc"))

    def list(self):
        return [
            self.get(p.stem) for p in self.directory.iterdir() if p.suffix == ".zuliprc"
        ]


class ClientRepository(BaseModel):
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
