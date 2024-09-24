import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from zulip_write_only_proxy.models import AdminClient, ScopedClient
from zulip_write_only_proxy.repositories import ClientRepository


def test_file_creation():
    with tempfile.TemporaryDirectory() as f:
        path = Path(f) / "test.json"

        assert not path.exists()

        repository = ClientRepository(path=path)

        assert path.exists()

        assert len(repository.list()) == 0


def test_get_scoped_client(client_repo: ClientRepository):
    result = client_repo.get("client1")

    assert isinstance(result, ScopedClient)
    assert result.stream == "Test Stream 1"
    assert result.proposal_no == 1

    with pytest.raises(KeyError):
        client_repo.get("invalid")


def test_get_admin_client(client_repo: ClientRepository):
    result = client_repo.get("admin1")

    assert isinstance(result, AdminClient)
    assert result.admin is True


def test_put_scoped_client(client_repo: ClientRepository):
    client = ScopedClient(
        key="client3",  # type: ignore[arg-type]
        stream="Test Stream 3",
        proposal_no=3,
        bot_name="Test Bot 3",
    )

    client_repo.put(client)

    result = client_repo.get(client.token.get_secret_value())

    assert isinstance(result, ScopedClient)
    assert result.model_dump() == client.model_dump()

    await client_repo.delete(client._key)

    result = await client_repo.get(client._key)
    assert result is None
