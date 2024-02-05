from __future__ import annotations

from pathlib import Path
from typing import Annotated

import fastapi
import zulip
from pydantic import SecretStr

from . import models, mymdc, repositories

CLIENT_REPO: repositories.ClientRepository = None  # type: ignore
ZULIPRC_REPO: repositories.ZuliprcRepository = None  # type: ignore


def setup():
    global CLIENT_REPO, ZULIPRC_REPO
    CLIENT_REPO = repositories.ClientRepository(
        path=Path.cwd() / "config" / "clients.json"
    )
    ZULIPRC_REPO = repositories.ZuliprcRepository(directory=Path.cwd() / "config")


async def get_or_put_bot(
    proposal_no: int,
    bot_name: str | None = None,
    bot_email: str | None = None,
    bot_key: str | None = None,
    bot_site: str = "https://euxfel-da.zulipchat.com",
) -> zulip.Client:
    bot_name = bot_name or str(proposal_no)

    try:
        client = ZULIPRC_REPO.get(bot_name)
    except zulip.ConfigNotFoundError as e:
        if not bot_name or not bot_key or not bot_email:
            raise fastapi.HTTPException(
                status_code=422,
                detail=(
                    f"bot '{bot_name}' does not exist, to create it both the bot email "
                    "and key must be provided"
                ),
            ) from e
        bot = models.Bot(
            name=bot_name, email=bot_email, key=SecretStr(bot_key), site=bot_site
        )
        client = ZULIPRC_REPO.put(bot)

    return client


async def create_client(
    new_client: Annotated[models.ScopedClientCreate, fastapi.Depends()],
    _: Annotated[zulip.Client, fastapi.Depends(get_or_put_bot)],
) -> models.ScopedClient:
    if new_client.stream is None:
        new_client.stream = await mymdc.client.get_zulip_stream_name(
            new_client.proposal_no
        )

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


def list_clients() -> list[models.Client]:
    return CLIENT_REPO.list()
