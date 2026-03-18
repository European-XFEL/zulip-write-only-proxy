from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import Request, Response
from pydantic import SecretStr

from zwop.mymdc import (
    MyMdCAuth,
    MyMdCClient,
    NoStreamForProposalError,
)


def make_response(
    method: str, url: str, *, status_code: int = 200, json: dict | None = None
):
    return Response(
        status_code=status_code,
        json=json,
        request=Request(method, url),
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
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = make_response(
            "POST",
            str(mymdc_auth.token_url),
            json={
                "access_token": "test_token",
                "expires_in": 3600,
            },
        )
        mock_client_cls.return_value = mock_client

        token = await mymdc_auth.acquire_token()
        assert token == "test_token"  # noqa: S105
        assert mymdc_auth._access_token == "test_token"  # noqa: S105
        assert mymdc_auth._expires_at > datetime.now(tz=UTC)

        mock_client.post.assert_called_once()

        # check that token is reused
        await mymdc_auth.acquire_token()

        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_async_auth_flow(mymdc_auth):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = make_response(
            "POST",
            str(mymdc_auth.token_url),
            json={
                "access_token": "test_token",
                "expires_in": 3600,
            },
        )
        mock_client_cls.return_value = mock_client

        request = Request("GET", "http://test_url")
        async for req in mymdc_auth.async_auth_flow(request):
            assert req.headers["Authorization"] == "Bearer test_token"
            assert req.headers["accept"] == "application/json; version=1"
            assert req.headers["X-User-Email"] == "test_email"


@pytest.mark.asyncio
async def test_get_zulip_stream_name(mymdc_client):
    with patch.object(mymdc_client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = make_response(
            "GET",
            "https://in.xfel.eu/metadata/api/proposals/by_number/1",
            json={"logbook_info": {"logbook_identifier": "test_stream"}},
        )
        stream_name = await mymdc_client.get_zulip_stream_name(1)
        assert stream_name == "test_stream"


@pytest.mark.asyncio
async def test_get_zulip_stream_name_no_stream(mymdc_client):
    with patch.object(mymdc_client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = make_response(
            "GET",
            "https://in.xfel.eu/metadata/api/proposals/by_number/1",
            json={"logbook_info": {}},
        )
        with pytest.raises(NoStreamForProposalError):
            await mymdc_client.get_zulip_stream_name(1)


@pytest.mark.asyncio
async def test_get_zulip_stream_name_invalid_stream(mymdc_client):
    with patch.object(mymdc_client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = make_response(
            "GET",
            "https://in.xfel.eu/metadata/api/proposals/by_number/1",
            json={"logbook_info": {"logbook_identifier": 123}},
        )
        with pytest.raises(RuntimeError):
            await mymdc_client.get_zulip_stream_name(1)
