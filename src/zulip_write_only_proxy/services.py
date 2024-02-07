from __future__ import annotations

from pathlib import Path
from typing import Annotated

import fastapi

from . import models, mymdc, repositories

CLIENT_REPO: repositories.ClientRepository = None  # type: ignore[assignment]
ZULIPRC_REPO: repositories.ZuliprcRepository = None  # type: ignore[assignment]


def setup():
    """Set up the repositories for the services. This should be called before
    any of the other functions in this module."""
    global CLIENT_REPO, ZULIPRC_REPO
    CLIENT_REPO = repositories.ClientRepository(
        path=Path.cwd() / "config" / "clients.json"
    )
    ZULIPRC_REPO = repositories.ZuliprcRepository(directory=Path.cwd() / "config")


async def create_client(
    new_client: Annotated[models.ScopedClientCreate, fastapi.Depends()],
) -> models.ScopedClient:
    if new_client.stream is None:
        new_client.stream = await mymdc.client.get_zulip_stream_name(
            new_client.proposal_no
        )

    bot_name = new_client.bot_name or str(new_client.proposal_no)
    key, email, site = new_client.bot_key, new_client.bot_email, new_client.bot_site

    if bot_name not in ZULIPRC_REPO.list():
        if not key or not email:
            key, email = await mymdc.client.get_zulip_bot_credentials(
                new_client.proposal_no
            )

        if not key or not email:
            raise fastapi.HTTPException(
                status_code=422,
                detail=(
                    f"bot '{bot_name}' does not exist, and a bot could not "
                    f"be found for proposal '{new_client.proposal_no}' via MyMdC. To "
                    "add a client with a new bot provide both bot_email bot_key."
                ),
            )

        ZULIPRC_REPO.put(bot_name, email, key, site)

    client = models.ScopedClient.model_validate(new_client, from_attributes=True)

    CLIENT_REPO.put(client)

    return client


def create_admin() -> models.AdminClient:
    client = models.AdminClient(admin=True)
    CLIENT_REPO.put(client)
    return client


def get_client(key: str) -> models.Client:
    client = CLIENT_REPO.get(key)

    if isinstance(client, models.ScopedClient):
        client._client = ZULIPRC_REPO.get(client.bot_name)

    return client


def list_clients() -> list[models.ScopedClient]:
    return CLIENT_REPO.list()
