import asyncio
from typing import TYPE_CHECKING, Annotated

import fastapi
import zulip

from . import logger, models, mymdc, repositories

if TYPE_CHECKING:
    from .settings import Settings

CLIENT_REPO: repositories.BaseRepository = None  # type: ignore[assignment]
ZULIPRC_REPO: repositories.BaseRepository = None  # type: ignore[assignment]


def configure(settings: "Settings", _: fastapi.FastAPI):
    """Set up the repositories for the services. This should be called before
    any of the other functions in this module."""
    global CLIENT_REPO, ZULIPRC_REPO

    ZULIPRC_REPO = repositories.BaseRepository(
        file=settings.config_dir / "zuliprc.json",
        index="name",
        model=models.BotConfig,
    )

    CLIENT_REPO = repositories.BaseRepository(
        file=settings.config_dir / "clients.json",
        index="key",
        model=models.ScopedClient,
    )

    logger.info(
        "Setting up repositories", client_repo=CLIENT_REPO, zuliprc_repo=ZULIPRC_REPO
    )

    asyncio.create_task(CLIENT_REPO.load())  # noqa: RUF006
    asyncio.create_task(ZULIPRC_REPO.load())  # noqa: RUF006


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

    name = new_client.bot_name or new_client.proposal_no
    key, email, site = (new_client.bot_key, new_client.bot_email, new_client.bot_site)
    _id = None

    if name not in await ZULIPRC_REPO.list():
        logger.debug("Bot zuliprc not present")
        if not all((key, email, site)):
            _id, key, email, site = await mymdc.CLIENT.get_zulip_bot_credentials(
                new_client.proposal_no
            )
            logger.debug(
                "Bot credentials from MyMdC",
                bot_name=name,
                bot_email=email,
                bot_key=key,
                bot_id=_id,
            )

        if not key or not email:
            raise fastapi.HTTPException(
                status_code=422,
                detail=(
                    f"bot '{name}' does not exist, and a bot could not "
                    f"be found for proposal '{new_client.proposal_no}' via MyMdC. To "
                    "add a client with a new bot provide both bot_email bot_key."
                ),
            )

        if not _id:
            profile = zulip.Client(email=email, api_key=key, site=site).get_profile()
            _id = profile.get("user_id")
            if not _id:
                raise fastapi.HTTPException(
                    status_code=422,
                    detail=(
                        f"could not get bot id from zulip for bot '{name=}, {email=}'."
                    ),
                )

        bot = models.BotConfig(
            name=str(name),
            id=_id,
            api_key=key,  # type: ignore[arg-type]
            email=email,
            site=site,  # type: ignore[arg-type]
        )

        await ZULIPRC_REPO.insert(bot)
    else:
        bot = await ZULIPRC_REPO.get(str(name))

    client = models.ScopedClient.model_validate({
        **new_client.model_dump(),
        "created_by": created_by,
        "bot_id": bot.id,
        "bot_name": bot.name,
    })

    await CLIENT_REPO.insert(client)

    logger.info("Created client", client=client)

    return client


async def get_client(key: str | None) -> models.ScopedClient:
    if key is None:
        raise fastapi.HTTPException(status_code=403, detail="Not authenticated")

    try:
        client = await CLIENT_REPO.get(key)
    except KeyError as e:
        raise fastapi.HTTPException(
            status_code=401, detail="Unauthorised", headers={"HX-Location": "/"}
        ) from e

    try:
        bot_config = await ZULIPRC_REPO.get(client.bot_name)
    except KeyError as e:
        raise fastapi.HTTPException(
            status_code=401, detail="Bot configuration not found"
        ) from e

    client._client = zulip.Client(
        email=bot_config.email,
        api_key=bot_config.api_key.get_secret_value(),
        site=str(bot_config.site),
    )

    return client


async def get_bot(bot_name: str) -> models.BotConfig:
    return await ZULIPRC_REPO.get(bot_name)


async def list_clients() -> list[models.ScopedClientWithKey]:
    return await CLIENT_REPO.list()
