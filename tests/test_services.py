from unittest.mock import patch

import pytest

from zulip_write_only_proxy.models import AdminClient, ScopedClient
from zulip_write_only_proxy.services import (
    create_admin,
    create_client,
    get_client,
    list_clients,
    setup,
)


def test_create_client(repository):
    result = create_client(proposal_no=3)
    assert isinstance(result, ScopedClient)


def test_create_admin(repository):
    result = create_admin()
    assert isinstance(result, AdminClient)


def test_get_client(repository):
    result = get_client("client1")

    assert isinstance(result, ScopedClient)
    assert result.stream == "Test Stream 1"
    assert result.proposal_no == 1

    with pytest.raises(KeyError):
        get_client("invalid")


def test_list_clients(repository):
    result = list_clients()
    assert len(result) == 3


def test_setup(zulip_client):
    from pydantic.fields import ModelPrivateAttr
    from pydantic_core import PydanticUndefinedType

    with patch.object(ScopedClient, "_client", ModelPrivateAttr()):
        assert isinstance(ScopedClient._client, ModelPrivateAttr)
        assert isinstance(ScopedClient._client.default, PydanticUndefinedType)

        setup()

        assert not isinstance(ScopedClient._client.default, PydanticUndefinedType)


def test_setup_raises(zulip_client):
    with patch.object(ScopedClient, "_client", 1234):
        with pytest.raises(RuntimeError):
            setup()
