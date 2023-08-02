from __future__ import annotations

from pathlib import Path

import zulip
from pydantic.fields import ModelPrivateAttr
from pydantic_core import PydanticUndefined

from .model import AdminClient, Client, ScopedClient
from .repository import JSONRepository

REPOSITORY = JSONRepository(path=Path.cwd() / "clients.json")


def create_client(proposal_no: int, stream: str | None = None) -> ScopedClient:
    client = ScopedClient.create(proposal_no, stream)
    REPOSITORY.put(client)
    return client


def create_admin() -> AdminClient:
    client = AdminClient.create()
    REPOSITORY.put_admin(client)
    return client


def get_client(key: str) -> Client:
    return REPOSITORY.get(key)


def list_clients() -> list[ScopedClient]:
    return REPOSITORY.list()


def setup():
    if not isinstance(ScopedClient._client, ModelPrivateAttr):
        raise RuntimeError("ScopedClient.client is not a ModelPrivateAttr")

    client_default = ScopedClient._client.default

    if client_default is None or client_default is PydanticUndefined:
        zulip_client = zulip.Client(config_file=str(Path.cwd() / "zuliprc"))
        ScopedClient._client.default = zulip_client
