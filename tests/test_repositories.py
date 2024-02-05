import tempfile
from pathlib import Path

import pytest

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

    result = client_repo.get(client.key.get_secret_value())

    assert isinstance(result, ScopedClient)
    assert result.stream == "Test Stream 3"
    assert result.proposal_no == 3
    assert result.bot_name == "Test Bot 3"


def test_put_admin_client(client_repo: ClientRepository):
    client = AdminClient(key="admin2", admin=True)  # type: ignore[arg-type]

    client_repo.put(client)

    result = client_repo.get(client.key.get_secret_value())

    assert isinstance(result, AdminClient)
    assert result.admin is True


def test_list_clients(client_repo: ClientRepository):
    result = client_repo.list()

    assert len(result) == 3

    assert isinstance(result[0], ScopedClient)
    assert result[0].stream == "Test Stream 1"
    assert result[0].proposal_no == 1

    assert isinstance(result[1], ScopedClient)
    assert result[1].stream == "Test Stream 2"
    assert result[1].proposal_no == 2

    assert isinstance(result[2], AdminClient)
    assert result[2].key.get_secret_value() == "admin1"
    assert result[2].admin is True
