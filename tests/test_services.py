from unittest.mock import MagicMock, patch

import pytest

from zulip_write_only_proxy import services
from zulip_write_only_proxy.models import AdminClient, ScopedClient, ScopedClientCreate
from zulip_write_only_proxy.repositories import JSONRepository


@pytest.mark.asyncio
async def test_create_client(repository: JSONRepository):
    result = await services.create_client(
        ScopedClientCreate(proposal_no=1234, stream="Test Stream")
    )
    assert isinstance(result, ScopedClient)


def test_create_admin(repository: JSONRepository):
    result = services.create_admin()
    assert isinstance(result, AdminClient)


def test_get_client(repository: JSONRepository):
    result = services.get_client("client1")

    assert isinstance(result, ScopedClient)
    assert result.stream == "Test Stream 1"
    assert result.proposal_no == 1

    with pytest.raises(KeyError):
        services.get_client("invalid")


def test_list_clients(repository: JSONRepository):
    result = services.list_clients()
    assert len(result) == 3
