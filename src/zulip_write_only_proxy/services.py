import asyncio
import datetime
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

import fastapi
import orjson
import zulip
from pydantic import SecretStr
from pydantic_core import Url

from . import _remote_receive, logger, models, mymdc, repositories
from .models.client import NoBotForClientError
from .settings import Settings, settings

if TYPE_CHECKING:
    from os import PathLike

CLIENT_REPO: repositories.BaseRepository[models.ScopedClient] = None  # type: ignore[assignment,type-var]
ZULIPRC_REPO: repositories.BaseRepository[models.BotConfig] = None  # type: ignore[assignment,type-var]


async def configure(settings: Settings, _: fastapi.FastAPI | None):
    """Set up the repositories for the services. This should be called before
    any of the other functions in this module."""
    global CLIENT_REPO, ZULIPRC_REPO

    ZULIPRC_REPO = repositories.BaseRepository(
        file=settings.config_dir / "zuliprc.json",
        model=models.BotConfig,
    )

    CLIENT_REPO = repositories.BaseRepository(
        file=settings.config_dir / "clients.json",
        model=models.ScopedClient,
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
        site=Url(bot_site),
        created_at=created_at or datetime.datetime.now(tz=datetime.timezone.utc),
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
        if "Logbook hasn't been created for proposal" not in str(e.detail):
            raise e

        bot = None
        logger.warning(
            "No logbook found for proposal", proposal_no=new_client.proposal_no
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


async def get_bot(bot_name: str) -> models.BotConfig | None:
    return await ZULIPRC_REPO.get(bot_name)


async def list_clients() -> list[models.ScopedClient]:
    return await CLIENT_REPO.list()


async def write_tokens(
    proposal_no: int,
    kinds: Annotated[list[Literal["zulip", "mymdc"]], fastapi.Query(...)],
    overwrite: bool = False,
    dry_run: bool = False,
    created_by: str = "write_tokens",
):
    details: dict[str, Any] = {"created_client": False}

    version = await _call_remote_receive("--version")

    client = await CLIENT_REPO.get(proposal_no, by="proposal_no")
    if client is None:
        details["created_client"] = True
        client = await create_client(
            models.ScopedClientCreate(proposal_no=proposal_no),
            created_by,
        )

    queue = {}
    for _kind in kinds:
        kind = (
            _remote_receive.MymdcConfig
            if _kind == "mymdc"
            else _remote_receive.ZulipConfig
        )
        config = kind(
            key=client.token.get_secret_value(),
            zwop_url=str(settings.token_writer.zwop_url),
        )
        data = orjson.dumps(config).decode()
        queue[_kind] = asyncio.create_task(
            _call_remote_receive(
                str(proposal_no),
                _kind,
                data,
                "--dry-run" if dry_run else "",
                "--overwrite" if overwrite else "",
            )
        )

    await asyncio.wait(queue.values())

    details |= {k: v.result() for k, v in queue.items()}

    script_file_hash = hashlib.sha256(
        Path(_remote_receive.__file__).read_bytes()
    ).hexdigest()

    if version["hash"] != script_file_hash:
        logger.critical(
            "Remote script hash mismatch", version=version, local_hash=script_file_hash
        )
        details["version"] = version

    status_code = max(
        (d.get("status_code", 500) for d in details.values() if isinstance(d, dict)),
        default=500,
    )

    if status_code != 200:
        raise fastapi.HTTPException(
            status_code=status_code,
            detail={
                "msg": "error writing token(s)",
                "details": details,
            },
        )

    return details


async def _call_remote_receive(*args: str):
    base_cmd: list[str | PathLike] = [
        "ssh",
        "-F",
        "/dev/null",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={settings.token_writer.ssh_known_hosts}",
        "-i",
        settings.token_writer.ssh_private_key,
        settings.token_writer.ssh_destination,
        "--",
    ]

    cmd = base_cmd.copy()
    cmd.extend(args)

    logger.debug("Calling", cmd=cmd)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    logger.info("Subprocess response", stdout=stdout, stderr=stderr)

    try:
        stdout_dict = orjson.loads(stdout)
    except orjson.JSONDecodeError:
        stdout_dict = {"stdout": stdout.decode()}

    try:
        stderr_dict = orjson.loads(stderr)
    except orjson.JSONDecodeError:
        stderr_dict = {"stderr": stderr.decode()}

    return {"returncode": process.returncode, **stdout_dict, **stderr_dict}
