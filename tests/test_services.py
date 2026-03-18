from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from zwop.models import ScopedClient, ScopedClientCreate
from zwop.mymdc import MyMdCResponseError

from zwop import services


@pytest.mark.asyncio
async def test_create_client(client_repo, zuliprc_repo, mock_mymdc_client):
    client = ScopedClientCreate(
        proposal_no=11234,
        stream="Another Test Stream",
        bot_id=2,
        bot_site="http://a-site.com",
        token=SecretStr("another-secret"),
        created_at=datetime.fromisoformat("2021-01-01Z00:00:00"),
    )

    result = await services.create_client(
        client,
        "foo",
        client_repo,
        zuliprc_repo,
        mock_mymdc_client,
    )
    assert isinstance(result, ScopedClient)


@pytest.mark.asyncio
async def test_create_client_no_bot(client_repo, zuliprc_repo):
    import httpx

    client = ScopedClientCreate(
        proposal_no=111234,
        stream="Another Test Stream",
        bot_id=None,
        token=SecretStr("another-secret"),
        created_at=datetime.fromisoformat("2021-01-01Z00:00:00"),
    )

    mock_mymdc = AsyncMock()
    mock_mymdc.get_zulip_bot_credentials.side_effect = MyMdCResponseError(
        httpx.Response(status_code=403, json="{}")
    )
    mock_mymdc.get_proposal_id.return_value = 111234
    result = await services.create_client(client, "bar", client_repo, zuliprc_repo, mock_mymdc)

    assert isinstance(result, ScopedClient)
    assert result.bot_id is None


@pytest.mark.asyncio
async def test_get_client(a_scoped_client, client_repo, zuliprc_repo):
    result = await services.get_client(
        a_scoped_client.token.get_secret_value(), client_repo, zuliprc_repo
    )

    assert isinstance(result, ScopedClient)
    assert a_scoped_client.model_dump_json() == result.model_dump_json()

    with pytest.raises(HTTPException):
        await services.get_client("invalid", client_repo, zuliprc_repo)
