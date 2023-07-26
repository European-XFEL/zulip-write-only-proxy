from pathlib import Path

import zulip

from .model import ScopedClient
from .repository import JSONRepository

REPOSITORY = JSONRepository(path=Path(__file__).parent / "clients.json")


def create_client(proposal_no: int) -> ScopedClient:
    client = ScopedClient.create(proposal_no)
    REPOSITORY.put(client)
    return client


def get_client(key: str) -> ScopedClient:
    return REPOSITORY.get(key)


def list_clients() -> list[ScopedClient]:
    return REPOSITORY.list()


def setup():
    if ScopedClient._client is not None:
        print("Client already set up")
        return

    zulip_client = zulip.Client(config_file=str(Path(__file__).parent / "zuliprc"))
    ScopedClient._client = zulip_client
