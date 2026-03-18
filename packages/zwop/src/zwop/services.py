import asyncio
import contextlib
import datetime
import ssl
from http.client import OK
from typing import Annotated, Literal

import fastapi
import httpx
import zulip
import zwop_tws as tws
from pydantic import HttpUrl, SecretStr

from . import logger, models, mymdc, repositories
from .models.client import NoBotForClientError
from .settings import Settings, settings

CLIENT_REPO: repositories.BaseRepository[models.ScopedClient] = None  # type: ignore[assignment,type-var]
ZULIPRC_REPO: repositories.BaseRepository[models.BotConfig] = None  # type: ignore[assignment,type-var]
TOKEN_WRITER_CLIENT: httpx.AsyncClient = None  # type: ignore[assignment]


async def configure(s: Settings, _: fastapi.FastAPI | None):
    """Set up repositories and the mTLS HTTP client for the token-writer service."""
    global CLIENT_REPO, ZULIPRC_REPO, TOKEN_WRITER_CLIENT, settings

    settings = s

    ZULIPRC_REPO = repositories.BaseRepository(
        file=s.config_dir / "zuliprc.json",
        model=models.BotConfig,
    )

    CLIENT_REPO = repositories.BaseRepository(
        file=s.config_dir / "clients.json",
        model=models.ScopedClient,
    )

    logger.info(
        "Setting up repositories", client_repo=CLIENT_REPO, zuliprc_repo=ZULIPRC_REPO
    )

    await CLIENT_REPO.load()
    await ZULIPRC_REPO.load()

    ctx = ssl.create_default_context(cafile=str(s.token_writer.ca_file.absolute()))
    ctx.load_cert_chain(
        certfile=str(s.token_writer.cert_file.absolute()),
        keyfile=str(s.token_writer.key_file.absolute()),
    )

    TOKEN_WRITER_CLIENT = httpx.AsyncClient(
        verify=ctx, base_url=str(s.token_writer.url)
    )

    logger.info("Configured token writer service", **s.token_writer.model_dump())


async def get_or_create_bot(
    proposal_no: int,
    bot_email: str | None = None,
    bot_key: str | None = None,
    bot_site: str = "https://mylog.connect.xfel.eu/",
    bot_id: int | None = None,
) -> models.BotConfig:
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
        site=HttpUrl(bot_site),
        created_at=created_at or datetime.datetime.now(tz=datetime.UTC),
        proposal_no=proposal_no,
    )

    with contextlib.suppress(repositories.EntryExistsException):
        await ZULIPRC_REPO.insert(bot)

    return bot


async def create_client(
    new_client: Annotated[models.ScopedClientCreate, fastapi.Depends()],
    created_by: str,
) -> models.ScopedClient:
    logger.info("Creating client", new_client=new_client, created_by=created_by)

    if new_client.stream is None:
        try:
            new_client.stream = await mymdc.CLIENT.get_zulip_stream_name(
                new_client.proposal_no
            )
            logger.debug("Stream name from MyMdC", stream=new_client.stream)
        except mymdc.NoStreamForProposalError:
            logger.warning("No stream name found", proposal_no=new_client.proposal_no)

    try:
        bot = await get_or_create_bot(
            new_client.proposal_no,
            bot_id=new_client.bot_id,
            bot_site=new_client.bot_site,
        )
    except mymdc.MyMdCResponseError as e:
        bot = None
        logger.warning(
            "No logbook found for proposal", proposal_no=new_client.proposal_no, exc=e
        )

    client = models.ScopedClient(
        proposal_no=new_client.proposal_no,
        proposal_id=await mymdc.CLIENT.get_proposal_id(new_client.proposal_no),
        stream=new_client.stream,
        bot_id=bot.id if bot else None,
        bot_site=bot.site if bot else None,
        token=new_client.token,
        created_at=new_client.created_at,
        created_by=created_by,
    )

    await CLIENT_REPO.insert(client)

    logger.info("Created client", client=client)

    return client


async def delete_client(key: str) -> str:
    return await CLIENT_REPO.delete(key, by="token")


async def get_client(key: str | None) -> models.ScopedClient:
    if key is None:
        raise fastapi.HTTPException(status_code=403, detail="Not authenticated")

    client = await CLIENT_REPO.get(key, by="token")

    if client is None:
        raise fastapi.HTTPException(
            status_code=401, detail="Unauthorised", headers={"HX-Location": "/"}
        )

    try:
        bot = await ZULIPRC_REPO.get(client._bot_key)

        if bot is None:
            raise fastapi.HTTPException(
                status_code=401,
                detail=f"Bot configuration not found for {client._bot_key}",
            )

        client._client = zulip.Client(
            email=bot.email,
            api_key=bot.key.get_secret_value(),
            site=str(bot.site),
        )
    except NoBotForClientError as e:
        logger.warning("No bot for client", client=client, error=e)

    return client


async def get_bot(bot_key: str) -> models.BotConfig | None:
    return await ZULIPRC_REPO.get(bot_key)


async def list_clients() -> list[models.ScopedClient]:
    return await CLIENT_REPO.list()


async def write_tokens(
    proposal_no: int,
    kinds: Annotated[list[Literal["zulip", "mymdc"]], fastapi.Query(...)],
    overwrite: bool = False,
    dry_run: bool = False,
    created_by: str = "write_tokens",
) -> tws.FileWriteSummary:
    client = await CLIENT_REPO.get(proposal_no, by="proposal_no")
    if client is None:
        client = await create_client(
            models.ScopedClientCreate(proposal_no=proposal_no),
            created_by,
        )

    tasks = {
        k: asyncio.create_task(
            TOKEN_WRITER_CLIENT.post(
                "/v1/write",
                content=tws.FileWriteRequest(
                    proposal_no=proposal_no,
                    kind=k,
                    key=client.token.get_secret_value(),
                    zwop_url=settings.token_writer.zwop_url,
                    overwrite=overwrite,
                    dry_run=dry_run,
                ).model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
        )
        for k in kinds
    }

    await asyncio.wait(tasks.values())

    results: list[tws.FileWriteResult] = []
    status_code = OK
    for task in tasks.values():
        resp = task.result()
        result = tws.FileWriteResult.model_validate(resp.json())
        results.append(result)
        if result.status_code != OK:
            status_code = result.status_code

    if status_code != OK:
        raise fastapi.HTTPException(
            status_code=status_code,
            detail={
                "msg": "error writing token(s)",
                "results": [r.model_dump() for r in results],
            },
        )

    return tws.FileWriteSummary(
        proposal=proposal_no,
        results=results,
        status_code=status_code,
    )
