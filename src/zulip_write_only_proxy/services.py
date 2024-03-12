import datetime
from typing import TYPE_CHECKING, Annotated

import fastapi
import zulip
from pydantic import SecretStr
from pydantic_core import Url

from . import logger, models, mymdc, repositories

if TYPE_CHECKING:
    from .settings import Settings

CLIENT_REPO: repositories.BaseRepository[models.ScopedClient] = None  # type: ignore[assignment]
ZULIPRC_REPO: repositories.BaseRepository[models.BotConfig] = None  # type: ignore[assignment]


async def configure(settings: "Settings", _: fastapi.FastAPI | None):
    """Set up the repositories for the services. This should be called before
    any of the other functions in this module."""
    global CLIENT_REPO, ZULIPRC_REPO

    ZULIPRC_REPO = repositories.BaseRepository(
        file=settings.config_dir / "zuliprc.json",
        model=models.BotConfig,  # type: ignore[assignment]
    )

    CLIENT_REPO = repositories.BaseRepository(
        file=settings.config_dir / "clients.json",
        model=models.ScopedClient,  # type: ignore[assignment]
    )

    logger.info(
        "Setting up repositories", client_repo=CLIENT_REPO, zuliprc_repo=ZULIPRC_REPO
    )

    await CLIENT_REPO.load()
    await ZULIPRC_REPO.load()


async def get_or_create_bot(
    proposal_no: int,
    bot_email: str | None = None,
    bot_key: str | None = None,
    bot_site: str = "https://mylog.connect.xfel.eu/",
    bot_id: int | None = None,
):
    created_at = None

    if bot_site and bot_id and (bot := await ZULIPRC_REPO.get(f"{bot_site}/{bot_id}")):
        return bot

    if not bot_email or not bot_key:
        res = await mymdc.CLIENT.get_zulip_bot_credentials(proposal_no)
        bot_email = res.get("bot_email")
        bot_key = res.get("bot_key")

    if not bot_email or not bot_key:
        raise fastapi.HTTPException(
            status_code=422,
            detail=(
                f"A bot could not be found for proposal '{proposal_no}' via "
                "MyMdC. To add a client with a new bot provide both bot_email bot_key."
            ),
        )

    if not bot_id:
        profile = zulip.Client(
            email=bot_email, api_key=bot_key, site=bot_site
        ).get_profile()
        bot_id = profile.get("user_id")
        created_at = profile.get("date_joined")

    if not bot_id:
        raise fastapi.HTTPException(
            status_code=422,
            detail=(
                f"could not get bot id from zulip for bot '{bot_email=}, {bot_site=}'."
            ),
        )

    bot = models.BotConfig(
        id=bot_id,
        key=SecretStr(bot_key),
        email=bot_email,
        site=Url(bot_site),
        created_at=created_at or datetime.datetime.utcnow(),
        proposal_no=proposal_no,
    )

    await ZULIPRC_REPO.insert(bot)

    return bot


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

    bot = await get_or_create_bot(
        new_client.proposal_no, bot_id=new_client.bot_id, bot_site=new_client.bot_site
    )

    client = models.ScopedClient(
        proposal_no=new_client.proposal_no,
        stream=new_client.stream,
        bot_id=bot.id,
        bot_site=bot.site,
        token=new_client.token,
        created_at=new_client.created_at,
        created_by=created_by,
    )

    await CLIENT_REPO.insert(client)

    logger.info("Created client", client=client)

    return client


async def get_client(key: str | None) -> models.ScopedClient:
    if key is None:
        raise fastapi.HTTPException(status_code=403, detail="Not authenticated")

    client = await CLIENT_REPO.get(key, by="token")

    if client is None:
        raise fastapi.HTTPException(
            status_code=401, detail="Unauthorised", headers={"HX-Location": "/"}
        )

    bot = await ZULIPRC_REPO.get(client._bot_key)

    if bot is None:
        raise fastapi.HTTPException(
            status_code=401, detail=f"Bot configuration not found for {client._bot_key}"
        )

    client._client = zulip.Client(
        email=bot.email,
        api_key=bot.key.get_secret_value(),
        site=str(bot.site),
    )

    return client


async def get_bot(bot_name: str) -> models.BotConfig | None:
    return await ZULIPRC_REPO.get(bot_name)


async def list_clients() -> list[models.ScopedClient]:
    return await CLIENT_REPO.list()
