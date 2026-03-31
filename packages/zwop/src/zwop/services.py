import asyncio
import contextlib
import datetime
import ssl
from http.client import OK
from typing import Annotated, Literal

import fastapi
import httpx
import zulip
from authlib.integrations.starlette_client import OAuth
from pydantic import HttpUrl, SecretStr

import zwop_tws as tws
from . import logger, models, mymdc, repositories
from .models.client import NoBotForClientError
from .settings import Settings


async def configure_repo(app):
    settings = app.state.settings

    zuliprc_repo = repositories.BaseRepository(
        file=settings.config_dir / "zuliprc.json",
        model=models.BotConfig,
    )

    await zuliprc_repo.load()

    client_repo = repositories.BaseRepository(
        file=settings.config_dir / "clients.json",
        model=models.ScopedClient,
    )

    await client_repo.load()

    app.state.client_repo = client_repo
    app.state.zuliprc_repo = zuliprc_repo


async def configure_tws(app):  # noqa: RUF029
    settings = app.state.settings
    ctx = ssl.create_default_context(cafile=str(settings.tws.ca_file.absolute()))
    ctx.load_cert_chain(
        certfile=str(settings.tws.cert_file.absolute()),
        keyfile=str(settings.tws.key_file.absolute()),
    )
    app.state.tws_client = httpx.AsyncClient(
        verify=ctx, base_url=str(settings.tws.url)
    )


async def configure_oauth(app):  # noqa: RUF029
    settings = app.state.settings
    oauth_registry = OAuth()
    oauth_registry.register(
        name="dadev",
        client_id=settings.auth.client_id,
        client_secret=settings.auth.client_secret.get_secret_value(),
        server_metadata_url=str(settings.auth.server_metadata_url),
    )
    app.state.oauth = oauth_registry.dadev


async def configure(app: fastapi.FastAPI):
    async with asyncio.TaskGroup() as tg:
        tg.create_task(configure_repo(app))
        tg.create_task(configure_tws(app))
        tg.create_task(configure_oauth(app))


def get_client_repo(
    request: fastapi.Request,
) -> repositories.BaseRepository[models.ScopedClient]:
    return request.app.state.client_repo


def get_zuliprc_repo(
    request: fastapi.Request,
) -> repositories.BaseRepository[models.BotConfig]:
    return request.app.state.zuliprc_repo


def get_tws_client(request: fastapi.Request) -> httpx.AsyncClient:
    return request.app.state.tws_client


def get_settings(request: fastapi.Request) -> Settings:
    return request.app.state.settings


async def get_or_create_bot(
    proposal_no: int,
    zuliprc_repo: repositories.BaseRepository[models.BotConfig],
    mymdc_client: mymdc.MyMdCClient,
    bot_email: str | None = None,
    bot_key: str | None = None,
    bot_site: str = "https://mylog.connect.xfel.eu/",
    bot_id: int | None = None,
) -> models.BotConfig:
    created_at = None

    if bot_site and bot_id and (bot := await zuliprc_repo.get(f"{bot_site}/{bot_id}")):
        return bot

    if not bot_email or not bot_key:
        res = await mymdc_client.get_zulip_bot_credentials(proposal_no)
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
        await zuliprc_repo.insert(bot)

    return bot


async def create_client(
    new_client: models.ScopedClientCreate,
    created_by: str,
    client_repo: repositories.BaseRepository[models.ScopedClient],
    zuliprc_repo: repositories.BaseRepository[models.BotConfig],
    mymdc_client: mymdc.MyMdCClient,
) -> models.ScopedClient:
    logger.info("Creating client", new_client=new_client, created_by=created_by)

    if new_client.stream is None:
        try:
            new_client.stream = await mymdc_client.get_zulip_stream_name(
                new_client.proposal_no
            )
            logger.debug("Stream name from MyMdC", stream=new_client.stream)
        except mymdc.NoStreamForProposalError:
            logger.warning("No stream name found", proposal_no=new_client.proposal_no)

    try:
        bot = await get_or_create_bot(
            new_client.proposal_no,
            zuliprc_repo,
            mymdc_client,
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
        proposal_id=await mymdc_client.get_proposal_id(new_client.proposal_no),
        stream=new_client.stream,
        bot_id=bot.id if bot else None,
        bot_site=bot.site if bot else None,
        token=new_client.token,
        created_at=new_client.created_at,
        created_by=created_by,
    )

    await client_repo.insert(client)

    logger.info("Created client", client=client)

    return client


async def delete_client(
    key: str,
    client_repo: repositories.BaseRepository[models.ScopedClient],
) -> str:
    return await client_repo.delete(key, by="token")


async def get_client(
    key: str | None,
    client_repo: repositories.BaseRepository[models.ScopedClient],
    zuliprc_repo: repositories.BaseRepository[models.BotConfig],
) -> models.ScopedClient:
    if key is None:
        raise fastapi.HTTPException(status_code=403, detail="Not authenticated")

    client = await client_repo.get(key, by="token")

    if client is None:
        raise fastapi.HTTPException(
            status_code=401, detail="Unauthorised", headers={"HX-Location": "/"}
        )

    try:
        bot = await zuliprc_repo.get(client._bot_key)

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


async def get_bot(
    bot_key: str,
    zuliprc_repo: repositories.BaseRepository[models.BotConfig],
) -> models.BotConfig | None:
    return await zuliprc_repo.get(bot_key)


async def list_clients(
    client_repo: repositories.BaseRepository[models.ScopedClient],
) -> list[models.ScopedClient]:
    return await client_repo.list()


async def write_tokens(
    proposal_no: int,
    kinds: Annotated[list[Literal["zulip", "mymdc"]], fastapi.Query(...)],
    client_repo: Annotated[
        repositories.BaseRepository[models.ScopedClient],
        fastapi.Depends(get_client_repo),
    ],
    zuliprc_repo: Annotated[
        repositories.BaseRepository[models.BotConfig],
        fastapi.Depends(get_zuliprc_repo),
    ],
    mymdc_client: Annotated[
        mymdc.MyMdCClient,
        fastapi.Depends(mymdc.get_mymdc_client),
    ],
    tws_client: Annotated[
        httpx.AsyncClient,
        fastapi.Depends(get_tws_client),
    ],
    settings: Annotated[Settings, fastapi.Depends(get_settings)],
    overwrite: bool = False,
    dry_run: bool = False,
    created_by: str = "write_tokens",
) -> tws.FileWriteSummary:
    client = await client_repo.get(proposal_no, by="proposal_no")
    if client is None:
        client = await create_client(
            models.ScopedClientCreate(proposal_no=proposal_no),
            created_by,
            client_repo,
            zuliprc_repo,
            mymdc_client,
        )

    tasks = {
        k: asyncio.create_task(
            tws_client.post(
                "/v1/write",
                content=tws.FileWriteRequest(
                    proposal_no=proposal_no,
                    kind=k,
                    key=client.token.get_secret_value(),
                    zwop_url=settings.tws.zwop_url,
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
