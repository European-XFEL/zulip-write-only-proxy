import threading

import orjson
import zulip
from pydantic import BaseModel, DirectoryPath, FilePath, SecretStr, validate_call

from . import models

file_lock = threading.Lock()


class ZuliprcRepository(BaseModel):
    directory: DirectoryPath

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
        return [p.stem for p in self.directory.iterdir() if p.suffix == ".zuliprc"]


class ClientRepository(BaseModel):
    """A basic file/JSON-based repository for storing client entries."""

    path: FilePath

    def get(self, key: str) -> models.ScopedClient:
        data = orjson.loads(self.path.read_bytes())
        client_data = data[key]

        return models.ScopedClient(key=SecretStr(key), **client_data)

    def put(self, client: models.ScopedClient) -> None:
        with file_lock:
            data: dict[str, dict] = orjson.loads(self.path.read_bytes())
            data[client.key.get_secret_value()] = client.model_dump(exclude={"key"})
            self.path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    def list(self) -> list[models.ScopedClientWithKey]:
        data = orjson.loads(self.path.read_bytes())

        return [
            models.ScopedClientWithKey(key=key, **value) for key, value in data.items()
        ]
