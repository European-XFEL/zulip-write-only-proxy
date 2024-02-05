from __future__ import annotations

import typing

import pytest

from zulip_write_only_proxy import services
from zulip_write_only_proxy.models import AdminClient, ScopedClient, ScopedClientCreate

if typing.TYPE_CHECKING:
    from zulip_write_only_proxy.repositories import ClientRepository


@pytest.mark.asyncio
async def test_create_client(client_repo: ClientRepository):
    result = await services.create_client(
        ScopedClientCreate(proposal_no=1234, stream="Test Stream", bot_name="Test Bot"),
        _=await services.get_or_put_bot(
            1234, bot_name="Test Bot", bot_email="email", bot_key="key"
        ),
    )
    assert isinstance(result, ScopedClient)


@pytest.mark.asyncio
async def test_create_client_no_bot(client_repo: ClientRepository):
    result = await services.create_client(
        ScopedClientCreate(proposal_no=1234, stream="Test Stream", bot_name="Test Bot"),
        _=await services.get_or_put_bot(
            1234, bot_name="Test Bot", bot_email="email", bot_key=None
        ),
    )
    assert isinstance(result, ScopedClient)


def test_create_admin(client_repo: ClientRepository):
    result = services.create_admin()
    assert isinstance(result, AdminClient)


def test_get_client(client_repo: ClientRepository):
    result = services.get_client("client1")

    assert isinstance(result, ScopedClient)
    assert result.stream == "Test Stream 1"
    assert result.proposal_no == 1

    with pytest.raises(KeyError):
        services.get_client("invalid")


def test_list_clients(client_repo: ClientRepository):
    result = services.list_clients()
    assert len(result) == 3
