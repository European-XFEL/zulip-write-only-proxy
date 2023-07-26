from typing import Annotated, Optional

import typer
import uvicorn

from . import service

app = typer.Typer()


@app.command()
def create(
    proposal_no: Annotated[int, typer.Argument()],
    stream: Annotated[Optional[str], typer.Argument()] = None,
    topic: Annotated[Optional[str], typer.Argument()] = None,
):
    """Create a new scoped client for a proposal."""
    client = service.create_client(proposal_no, stream, topic)
    typer.echo(client)


@app.command()
def list():
    """List all scoped clients."""
    client = service.list_clients()
    typer.echo(client)


if __name__ == "__main__":
    app()
