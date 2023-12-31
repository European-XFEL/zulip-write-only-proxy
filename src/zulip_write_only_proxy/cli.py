from typing import Annotated

import typer

from . import models, services

app = typer.Typer()


@app.command()
def create(
    proposal_no: Annotated[int, typer.Argument()],
    stream: Annotated[str, typer.Argument()],
):
    """Create a new scoped client for a proposal."""
    services.setup()
    client = services.create_client(
        models.ScopedClientCreate(proposal_no=proposal_no, stream=stream)
    )
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
