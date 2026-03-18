import asyncio
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from pydantic import HttpUrl, SecretStr

from zwop.models import BotConfig, ScopedClient


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

    dotenv_file = config_dir / ".env"

    dotenv_file.write_text(
        f"""ZWOP_CONFIG_DIR={config_dir}
ZWOP_SESSION_SECRET=session_secret

ZWOP_MYMDC__ID=mymdc_id
ZWOP_MYMDC__SECRET=mymdc_secret
ZWOP_MYMDC__EMAIL=email@example.com
ZWOP_MYMDC__TOKEN_URL=http://foobar.local/token

ZWOP_AUTH__CLIENT_ID=client_id
ZWOP_AUTH__CLIENT_SECRET=client_secret
"""
    )

    os.environ["ZWOP_DOTENV_FILE"] = str(dotenv_file)

    from zwop.settings import configure

    return configure()


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
        bot_site=HttpUrl("http://a-site.com"),
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
        site=HttpUrl("http://a-site.com"),
        id=1,
        proposal_no=1234,
        created_at=datetime.fromisoformat("2021-01-01Z00:00:00"),
    )


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _services(settings, a_zuliprc, a_scoped_client):
    from zwop import models, repositories

    zuliprc_repo = repositories.BaseRepository(
        file=settings.config_dir / "zuliprc.json",
        model=models.BotConfig,
    )
    client_repo = repositories.BaseRepository(
        file=settings.config_dir / "clients.json",
        model=models.ScopedClient,
    )
    await client_repo.load()
    await zuliprc_repo.load()
    await client_repo.insert(a_scoped_client)
    await zuliprc_repo.insert(a_zuliprc)
    return {"client_repo": client_repo, "zuliprc_repo": zuliprc_repo}


@pytest.fixture(scope="session")
def client_repo(fastapi_client):
    return fastapi_client.app.state.client_repo


@pytest.fixture(scope="session")
def zuliprc_repo(fastapi_client):
    return fastapi_client.app.state.zuliprc_repo


@pytest.fixture(scope="session")
def mock_mymdc_client():
    mock = AsyncMock()
    mock.get_zulip_bot_credentials.return_value = {
        "logbook_name": None,
        "proposal_number": None,
        "bot_email": "email@email.com",
        "bot_key": "key",
        "name": None,
        "url": None,
        "bot_id": None,
        "status": None,
    }
    mock.get_proposal_id.return_value = 9999
    mock.get_zulip_stream_name.return_value = "Test Stream"
    return mock


@pytest.fixture(scope="session", autouse=True)
def fastapi_client(_services, mock_mymdc_client):
    from zwop import main

    app = main.create_app()

    with (
        patch("ssl.SSLContext.load_verify_locations"),
        patch("ssl.SSLContext.load_cert_chain"),
        TestClient(app, headers={"X-API-key": "secret"}) as client,
    ):
        app.state.mymdc_client = mock_mymdc_client
        yield client
