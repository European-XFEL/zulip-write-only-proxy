from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from zulip_write_only_proxy import services
from zulip_write_only_proxy.models import ScopedClient, ScopedClientCreate
from zulip_write_only_proxy.mymdc import MyMdCResponseError


@pytest.mark.asyncio
async def test_create_client():
    client = ScopedClientCreate(
        proposal_no=11234,
        stream="Another Test Stream",
        bot_id=2,
        bot_site="http://a-site.com",
        token=SecretStr("another-secret"),
        created_at=datetime.fromisoformat("2021-01-01Z00:00:00"),
    )

    result = await services.create_client(client, created_by="foo")
    assert isinstance(result, ScopedClient)


@pytest.mark.asyncio
async def test_create_client_no_bot():
    import httpx

    client = ScopedClientCreate(
        proposal_no=111234,
        stream="Another Test Stream",
        bot_id=None,
        token=SecretStr("another-secret"),
        created_at=datetime.fromisoformat("2021-01-01Z00:00:00"),
    )

    with patch(
        "zulip_write_only_proxy.mymdc.CLIENT", new_callable=AsyncMock
    ) as mock_class:
        mock_class.return_value = mock_class
        mock_class.get_zulip_bot_credentials.side_effect = MyMdCResponseError(
            httpx.Response(status_code=403, json="{}")
        )

        result = await services.create_client(client, created_by="bar")

    assert isinstance(result, ScopedClient)
    assert result.bot_id is None


@pytest.mark.asyncio
async def test_get_client(a_scoped_client):
    result = await services.get_client(a_scoped_client.token.get_secret_value())

    assert isinstance(result, ScopedClient)
    assert a_scoped_client.model_dump_json() == result.model_dump_json()

    with pytest.raises(HTTPException):
        await services.get_client("invalid")
