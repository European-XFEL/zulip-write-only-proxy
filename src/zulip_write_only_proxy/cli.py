from typing import Annotated, Optional

import typer
import uvicorn

from . import services

app = typer.Typer()


@app.command()
def create(
    proposal_no: Annotated[int, typer.Argument()],
    stream: Annotated[Optional[str], typer.Argument()] = None,
):
    """Create a new scoped client for a proposal."""
    client = services.create_client(proposal_no, stream)
    typer.echo(client)


@app.command()
def create_admin():
    """Create a new scoped client for a proposal."""
    client = services.create_admin()
    typer.echo(client)


@app.command()
def list():
    """List all scoped clients."""
    client = services.list_clients()
    typer.echo(client)


if __name__ == "__main__":
    app()
