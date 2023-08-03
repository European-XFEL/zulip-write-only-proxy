from unittest.mock import MagicMock, patch

import pytest

from zulip_write_only_proxy import services
from zulip_write_only_proxy.models import AdminClient, ScopedClient
from zulip_write_only_proxy.repositories import JSONRepository


def test_create_client(repository: JSONRepository):
    result = services.create_client(proposal_no=3)
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


def test_setup(zulip_client: MagicMock):
    from pydantic.fields import ModelPrivateAttr
    from pydantic_core import PydanticUndefinedType

    with patch.object(ScopedClient, "_client", ModelPrivateAttr()):
        assert isinstance(ScopedClient._client, ModelPrivateAttr)
        assert isinstance(ScopedClient._client.default, PydanticUndefinedType)
        assert ScopedClient._client.default_factory is None

        services.setup()

        assert not isinstance(
            ScopedClient._client.default_factory, PydanticUndefinedType
        )


def test_setup_raises(zulip_client: MagicMock):
    with patch.object(ScopedClient, "_client", 1234):
        with pytest.raises(RuntimeError):
            services.setup()
