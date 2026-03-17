import shutil
import ssl
from pathlib import Path

from anyio import Path as APath
from fastapi import FastAPI, HTTPException

from .models import (
    FileWriteRequest,
    FileWriteResult,
    TokenKind,
)
from .settings import settings

app = FastAPI(title="zwop-token-writer")


GPFS_ROOT = Path("/gpfs/exfel/exp")


async def _find_proposal_path(proposal_no: int) -> APath:
    paths = APath(GPFS_ROOT).glob(f"*/*/p{proposal_no:06d}")
    paths = [path async for path in paths]

    if not paths:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_no} not found")

    proposal_path = paths[0]

    if not await (proposal_path / "usr/Shared/amore").exists():
        raise HTTPException(
            status_code=404,
            detail=f"No amore directory for proposal {proposal_no}",
        )

    return proposal_path


async def _write_file(
    kind: TokenKind,
    target: APath,
    content: str,
    overwrite: bool,
    dry_run: bool,
    user: str,
    group: str,
    mode: int,
) -> FileWriteResult:
    if await target.exists() and not overwrite and not dry_run:
        return FileWriteResult(
            kind=kind,
            target=str(target),
            status_code=409,
            msg="file exists, not overwriting",
        )
    if dry_run:
        return FileWriteResult(
            kind=kind, target=str(target), status_code=200, msg="dry run"
        )
    await target.write_text(content)
    await target.chmod(mode)
    shutil.chown(target, user=user, group=group)
    return FileWriteResult(
        kind=kind, target=str(target), status_code=200, msg="wrote config file"
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/write")
async def write_file(request: FileWriteRequest) -> FileWriteResult:
    proposal_path = await _find_proposal_path(request.proposal_no)
    zwop_url = str(request.zwop_url)
    key = request.key

    if request.kind == "zulip":
        content = f"[ZULIP]\nkey = {key}\nurl = {zwop_url}\ntopics = []\n"
        result = await _write_file(
            "zulip",
            proposal_path / "usr/Shared/amore/zulip.cfg",
            content,
            request.overwrite,
            request.dry_run,
            "xdana",
            "exfel",
            0o666,
        )
    else:
        content = f"token: {key}\nserver: {zwop_url}\n"
        result = await _write_file(
            "mymdc",
            proposal_path / "usr/mymdc-credentials.yml",
            content,
            request.overwrite,
            request.dry_run,
            "xdana",
            "exfl_da",
            0o660,
        )

    return result


def run() -> None:
    import uvicorn

    uvicorn.run(
        "zwop_token_writer.main:app",
        host=settings.host,
        port=settings.port,
        ssl_keyfile=str(settings.mtls.key_file),
        ssl_certfile=str(settings.mtls.cert_file),
        ssl_ca_certs=str(settings.mtls.client_ca_file),
        ssl_cert_reqs=ssl.CERT_REQUIRED,
    )
