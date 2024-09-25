import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import SecretStr
from pydantic_core import Url

from zulip_write_only_proxy.models import ScopedClient
from zulip_write_only_proxy.repositories import BaseRepository


@pytest.mark.asyncio
async def test_file_creation():
    with tempfile.TemporaryDirectory() as f:
        path = Path(f) / "test.json"

        assert not path.exists()

        repo = BaseRepository(file=path, model=ScopedClient)

        await repo.write()

        assert path.exists()


@pytest.mark.asyncio
async def test_get_scoped_client(client_repo, a_scoped_client):
    result = await client_repo.get(a_scoped_client._key)

    assert isinstance(result, ScopedClient)

    assert result.model_dump() == a_scoped_client.model_dump()

    result = await client_repo.get("invalid")
    assert result is None


@pytest.mark.asyncio
async def test_list_clients(client_repo, a_scoped_client):
    result = await client_repo.list()

    assert len(result) == 1

    assert isinstance(result[0], ScopedClient)
    assert result[0].model_dump() == a_scoped_client.model_dump()


@pytest.mark.asyncio
async def test_insert_delete_scoped_client(client_repo):
    client = ScopedClient(
        proposal_no=11234,
        proposal_id=15678,
        stream="Another Test Stream",
        bot_id=1,
        bot_site=Url("http://a-site.com"),
        token=SecretStr("secret"),
        created_by="foo",
        created_at=datetime.fromisoformat("2021-01-01Z00:00:00"),
    )

    await client_repo.insert(client)

    result = await client_repo.get(client._key)

    assert isinstance(result, ScopedClient)
    assert result.model_dump() == client.model_dump()

    await client_repo.delete(client._key)

    result = await client_repo.get(client._key)
    assert result is None
