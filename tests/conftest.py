import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pydantic_core import Url

from zulip_write_only_proxy.models import BotConfig, ScopedClient
from zulip_write_only_proxy.settings import settings as base_settings


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def settings(tmp_path_factory):
    """Configure settings for tests.

    - Set the config_dir to a temporary directory
    - Remove credentials
    """
    config_dir = tmp_path_factory.mktemp("config")
    base_settings.config_dir = config_dir

    base_settings.auth.client_id = "client_id"
    base_settings.auth.client_secret = SecretStr("client_secret")

    base_settings.mymdc.secret = SecretStr("mymdc_secret")
    base_settings.mymdc.token_url = Url("http://foobar.local/token")

    return base_settings


@pytest.fixture(scope="session", autouse=True)
def zulip_client():
    with patch("zulip.Client", new_callable=MagicMock) as mock_class:
        mock_class.return_value = mock_class
        yield mock_class


@pytest.fixture(scope="session")
def a_scoped_client(zulip_client):
    client = ScopedClient(
        proposal_no=1234,
        proposal_id=5678,
        stream="Test Stream",
        bot_id=1,
        bot_site=Url("http://a-site.com"),
        token=SecretStr("secret"),
        created_by="foo",
        created_at=datetime.fromisoformat("2021-01-01Z00:00:00"),
    )
    client._client = zulip_client
    return client


@pytest.fixture(scope="session")
def a_zuliprc():
    return BotConfig(
        email="foo@bar.com",
        key=SecretStr("secret"),
        site=Url("http://a-site.com"),
        id=1,
        proposal_no=1234,
        created_at=datetime.fromisoformat("2021-01-01Z00:00:00"),
    )


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _services(settings, a_zuliprc, a_scoped_client):
    from zulip_write_only_proxy import services

    await services.configure(settings, None)

    await services.CLIENT_REPO.insert(a_scoped_client)

    await services.ZULIPRC_REPO.insert(a_zuliprc)


@pytest_asyncio.fixture(scope="session")
def client_repo(_services):
    from zulip_write_only_proxy import services

    return services.CLIENT_REPO


@pytest_asyncio.fixture(scope="session")
def zuliprc_repo(_services):
    from zulip_write_only_proxy import services

    return services.ZULIPRC_REPO


@pytest.fixture(scope="session", autouse=True)
def mymdc_client():
    with patch(
        "zulip_write_only_proxy.mymdc.CLIENT", new_callable=AsyncMock
    ) as mock_class:
        mock_class.return_value = mock_class
        mock_class.get_zulip_bot_credentials.return_value = {
            "logbook_name": None,
            "proposal_number": None,
            "bot_email": "email@email.com",
            "bot_key": "key",
            "name": None,
            "url": None,
            "bot_id": None,
            "status": None,
        }
        yield mock_class


@pytest.fixture(scope="session", autouse=True)
def fastapi_client(_services, a_scoped_client, zulip_client):
    from zulip_write_only_proxy import main

    app = main.create_app()

    with TestClient(app, headers={"X-API-key": "secret"}) as client:
        yield client
