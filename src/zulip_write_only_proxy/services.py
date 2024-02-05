from __future__ import annotations

from pathlib import Path
from typing import Annotated

import fastapi
import zulip

from . import models, mymdc, repositories

REPOSITORY = repositories.JSONRepository(
    path=Path.cwd() / "config" / "clients.json",
    zuliprc_dir=Path.cwd() / "config",
)


async def create_or_load_bot(
    proposal_no: int,
    bot_name: str | None = None,
    bot_email: str | None = None,
    bot_key: str | None = None,
    bot_site: str = "https://euxfel-da.zulipchat.com",
) -> zulip.Client:
    bot_name = bot_name or str(proposal_no)

    zuliprc = Path.cwd() / "config" / f"{bot_name}.zuliprc"

    if not zuliprc.exists():
        if not bot_name or not bot_key or not bot_email:
            raise fastapi.HTTPException(
                status_code=422,
                detail=(
                    f"bot '{bot_name}' does not exist, to create it both the bot email "
                    "and key must be provided"
                ),
            )
        zuliprc.write_text(
            f"[api]\nemail={bot_email}\nkey={bot_key}\nsite={bot_site}\n"
        )

    return zulip.Client(config_file=str(zuliprc))


async def create_client(
    new_client: Annotated[models.ScopedClientCreate, fastapi.Depends()],
    _: Annotated[models.Bot, fastapi.Depends(create_or_load_bot)],
) -> models.ScopedClient:
    if new_client.stream is None:
        new_client.stream = await mymdc.client.get_zulip_stream_name(
            new_client.proposal_no
        )

    client = models.ScopedClient.model_validate(new_client, from_attributes=True)

    REPOSITORY.put(client)

    return client


def create_admin() -> models.AdminClient:
    client = models.AdminClient(admin=True)
    REPOSITORY.put(client)
    return client


def get_client(key: str) -> models.Client:
    return REPOSITORY.get(key)


def list_clients() -> list[models.Client]:
    return REPOSITORY.list()
