from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import fastapi

from . import logger, models, mymdc, repositories

if TYPE_CHECKING:
    from .settings import Settings

CLIENT_REPO: repositories.ClientRepository = None  # type: ignore[assignment]
ZULIPRC_REPO: repositories.ZuliprcRepository = None  # type: ignore[assignment]


def configure(settings: "Settings", _: fastapi.FastAPI):
    """Set up the repositories for the services. This should be called before
    any of the other functions in this module."""
    global CLIENT_REPO, ZULIPRC_REPO
    logger.info(
        "Setting up repositories",
        client_repo=settings.clients.path,
        zuliprc_repo=settings.zuliprcs.directory,
    )
    CLIENT_REPO = repositories.ClientRepository(path=settings.clients.path)
    ZULIPRC_REPO = repositories.ZuliprcRepository(directory=settings.zuliprcs.directory)


async def create_client(
    new_client: Annotated[models.ScopedClientCreate, fastapi.Depends()],
    created_by: str,
) -> models.ScopedClient:
    logger.info("Creating client", new_client=new_client, created_by=created_by)

    if new_client.stream is None:
        new_client.stream = await mymdc.CLIENT.get_zulip_stream_name(
            new_client.proposal_no
        )
        logger.debug("Stream name from MyMdC", stream=new_client.stream)

    if new_client.bot_name is None:
        new_client.bot_name = str(new_client.proposal_no)
        logger.debug("Bot name from proposal number", bot_name=new_client.bot_name)

    bot_name = new_client.bot_name
    key, email, site = new_client.bot_key, new_client.bot_email, new_client.bot_site

    if bot_name not in ZULIPRC_REPO.list():
        logger.debug("Bot zuliprc not present")
        if not key or not email:
            key, email = await mymdc.CLIENT.get_zulip_bot_credentials(
                new_client.proposal_no
            )
            logger.debug("Bot credentials from MyMdC", bot_email=email, bot_key=key)

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

    _ = new_client.model_dump()
    _["created_by"] = created_by
    client = models.ScopedClient.model_validate(_)

    CLIENT_REPO.put(client)

    logger.info("Created client", client=client)

    return client


def get_client(key: str) -> models.ScopedClient:
    client = CLIENT_REPO.get(key)

    if isinstance(client, models.ScopedClient):
        client._client = ZULIPRC_REPO.get(client.bot_name)

    return client


def get_bot(bot_name: str):
    return ZULIPRC_REPO.get(bot_name)


def list_clients() -> list[models.ScopedClientWithKey]:
    return CLIENT_REPO.list()
