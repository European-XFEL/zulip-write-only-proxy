from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import Request
from pydantic import SecretStr

from zulip_write_only_proxy.mymdc import (
    MyMdCAuth,
    MyMdCClient,
    NoStreamForProposalError,
)


@pytest.fixture
def mymdc_auth():
    return MyMdCAuth(
        id="test_id",
        secret=SecretStr("test_secret"),
        email="test_email",
        token_url="http://test_url",  # type: ignore[assignment]  # noqa: S106
    )


@pytest.fixture
def mymdc_client(mymdc_auth):
    return MyMdCClient(auth=mymdc_auth)


@pytest.mark.asyncio
async def test_acquire_token(mymdc_auth):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json = Mock(
            return_value={
                "access_token": "test_token",
                "expires_in": 3600,
            }
        )
        token = await mymdc_auth.acquire_token()
        assert token == "test_token"  # noqa: S105
        assert mymdc_auth._access_token == "test_token"  # noqa: S105
        assert mymdc_auth._expires_at > datetime.now(tz=UTC)

        mock_post.assert_called_once()

        # check that token is reused
        await mymdc_auth.acquire_token()

        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_async_auth_flow(mymdc_auth):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json = Mock(
            return_value={
                "access_token": "test_token",
                "expires_in": 3600,
            }
        )
        request = Request("GET", "http://test_url")
        async for req in mymdc_auth.async_auth_flow(request):
            assert req.headers["Authorization"] == "Bearer test_token"
            assert req.headers["accept"] == "application/json; version=1"
            assert req.headers["X-User-Email"] == "test_email"


@pytest.mark.asyncio
async def test_get_zulip_stream_name(mymdc_client):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.json = Mock(
            return_value={"logbook_info": {"logbook_identifier": "test_stream"}}
        )
        stream_name = await mymdc_client.get_zulip_stream_name(1)
        assert stream_name == "test_stream"


@pytest.mark.asyncio
async def test_get_zulip_stream_name_no_stream(mymdc_client):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.json = Mock(return_value={"logbook_info": {}})
        with pytest.raises(NoStreamForProposalError):
            await mymdc_client.get_zulip_stream_name(1)


@pytest.mark.asyncio
async def test_get_zulip_stream_name_invalid_stream(mymdc_client):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.json = Mock(
            return_value={"logbook_info": {"logbook_identifier": 123}}
        )
        with pytest.raises(RuntimeError):
            await mymdc_client.get_zulip_stream_name(1)
