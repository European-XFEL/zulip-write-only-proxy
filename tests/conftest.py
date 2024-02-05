import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest
from fastapi.testclient import TestClient

from zulip_write_only_proxy.models import ScopedClient
from zulip_write_only_proxy.repositories import ClientRepository, ZuliprcRepository


@pytest.fixture
def client_repo():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        data = {
            "client1": {
                "stream": "Test Stream 1",
                "proposal_no": 1,
                "bot_name": "1",
            },
            "client2": {
                "stream": "Test Stream 2",
                "proposal_no": 2,
                "bot_name": "2",
            },
            "admin1": {
                "admin": True,
            },
        }

        f.write(orjson.dumps(data))

        path = Path(f.name)

    client_repo = ClientRepository(path=path)

    with patch("zulip_write_only_proxy.services.CLIENT_REPO", client_repo):
        yield client_repo

    path.unlink()


@pytest.fixture
def zuliprc_repo():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write_text("[api]\nemail=email\nkey=key\nsite=site\n")
        path = Path(f.name)

    zuliprc_repo = ZuliprcRepository(directory=path)

    with patch("zulip_write_only_proxy.services.ZULIPRC_REPO", zuliprc_repo):
        yield zuliprc_repo

    path.unlink()


@pytest.fixture
def scoped_client():
    client = ScopedClient(proposal_no=1234, stream="Test Stream", bot_name="Test Bot")
    client._client = MagicMock()
    return client


@pytest.fixture(autouse=True)
def zulip_client():
    with patch("zulip.Client", new_callable=MagicMock) as mock_class:
        mock_class.return_value = mock_class
        yield mock_class


@pytest.fixture(autouse=True)
def mymdc_client():
    with patch(
        "zulip_write_only_proxy.mymdc.client", new_callable=AsyncMock
    ) as mock_class:
        mock_class.return_value = mock_class
        yield mock_class


@pytest.fixture
def fastapi_client(client_repo, zulip_client):
    from zulip_write_only_proxy import main

    yield TestClient(main.app, headers={"X-API-key": "client1"})
