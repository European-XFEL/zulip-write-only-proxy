from __future__ import annotations

from pathlib import Path

import zulip
from pydantic.fields import ModelPrivateAttr
from pydantic_core import PydanticUndefined

from . import models, repositories

REPOSITORY = repositories.JSONRepository(path=Path.cwd() / "config" / "clients.json")


def create_client(client: models.ScopedClientCreate) -> models.ScopedClient:
    client = models.ScopedClient.model_validate(client, from_attributes=True)
    REPOSITORY.put(client)
    return client


def create_admin() -> models.AdminClient:
    client = models.AdminClient(admin=True)
    REPOSITORY.put(client)
    return client


def get_client(key: str) -> models.Client:
    return REPOSITORY.get(key)


def list_clients() -> list[models.Client]:
    return REPOSITORY.list()


def setup():
    if not isinstance(models.ScopedClient._client, ModelPrivateAttr):
        raise RuntimeError("ScopedClient.client is not a ModelPrivateAttr")

    client_default = models.ScopedClient._client.default

    if client_default is None or client_default is PydanticUndefined:
        zulip_client = zulip.Client(config_file=str(Path.cwd() / "config" / "zuliprc"))
        models.ScopedClient._client.default_factory = lambda: zulip_client
