#!/gpfs/exfel/sw/software/mambaforge/22.11/envs/202401/bin/python3

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import click
import orjson


@dataclass
class JSONError(Exception):
    msg: str
    details: dict
    status_code: int = 500

    def serialise(self):
        return orjson.dumps({
            "msg": self.msg,
            "status_code": self.status_code,
            **self.details,
        })


def validate_kind(ctx, param, value):
    kinds = ["zulip", "mymdc"]
    if value not in kinds:
        raise JSONError(
            msg="unknown kind",
            details={"kind": value, "kinds": kinds},
            status_code=422,
        )
    return value


def validate_data(ctx, param, value):
    try:
        return orjson.loads(value)
    except orjson.JSONDecodeError as e:
        msg = "data must be a valid JSON string"
        raise JSONError(msg, {"JSONDecodeError": e.msg}, status_code=422) from e


def validate_path(ctx, param, proposal):
    proposal_path = list(Path("/gpfs/exfel/exp").glob(f"*/*/p{proposal:06d}"))

    if not proposal_path:
        msg = "proposal not found"
        raise JSONError(msg, {"proposal": proposal}, status_code=404)

    if not (proposal_path[0] / "usr/Shared/amore").exists():
        msg = "no amore directory for proposal"
        raise JSONError(msg, {"proposal": proposal}, status_code=404)

    return proposal_path[0]


@dataclass
class ZulipConfig:
    key: str
    zwop_url: str
    topics: list[str] = field(default_factory=list)

    @property
    def text(self):
        return f"""[ZULIP]
key = {self.key}
url = {self.zwop_url}
topics = {self.topics}"""


@dataclass
class MymdcConfig:
    key: str
    zwop_url: str

    @property
    def text(self):
        return f"""token: {self.key}
server: {self.zwop_url}"""


def version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    path = Path(__file__).resolve()
    file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    _stat = path.stat()
    stat = {"mtime": _stat.st_mtime, "ctime": _stat.st_ctime, "mode": "0o644"}
    click.echo(
        JSONError(
            "version",
            {
                "shebang": path.read_text().splitlines()[0],
                "file": str(path),
                "hash": file_hash,
                "stat": stat,
            },
            status_code=200,
        ).serialise()
    )
    ctx.exit()


@click.command()
@click.option(
    "--version",
    default=False,
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=version,
)
@click.argument("proposal", callback=validate_path, required=True, type=int)
@click.argument("kind", callback=validate_kind, required=True, type=str)
@click.argument("data", callback=validate_data, required=True, type=str)
@click.option("--dry-run/--no-dry-run", default=False)
@click.option("--overwrite/--no-overwrite", default=False)
def cli(proposal, kind, data, dry_run, overwrite):
    """Process the given arguments."""
    config = None
    content = None
    target = None

    amore_dir = proposal / "usr/Shared/amore"

    if kind == "zulip":
        config = ZulipConfig(**data)
        target = amore_dir / "zulip.cfg"

    if kind == "mymdc":
        config = MymdcConfig(**data)
        target = amore_dir / "mymdc.cfg"

    res = {
        "proposal": str(proposal),
        "kind": kind,
        "target": str(target),
        "dry_run": dry_run,
        "overwrite": overwrite,
    }

    if not config or not target:
        msg = "error creating config object or target file path"
        raise JSONError(msg, res, status_code=500)

    if target.exists() and (not overwrite and not dry_run):
        msg = "file exists, not overwriting"
        raise JSONError(msg, res, status_code=409)

    content = config.text

    if not content:
        msg = "file content is empty"
        raise JSONError(msg, res, status_code=500)

    if dry_run:
        config.key = "**********"
        res["content"] = config.text
        click.echo(JSONError("dry run", res, status_code=200).serialise())
        return

    target.write_text(content)

    click.echo(JSONError("wrote config file", res, status_code=200).serialise())


if __name__ == "__main__":
    try:
        msg, data = cli()
    except JSONError as e:
        click.echo(e.serialise())
        exit(1)
    except Exception as e:
        click.echo(orjson.dumps({"uncaught error": str(e), "status_code": 500}))
        exit(1)
