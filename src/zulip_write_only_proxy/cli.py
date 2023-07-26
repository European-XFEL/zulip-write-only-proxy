import typer
import uvicorn

from . import service, main

app = typer.Typer()


@app.command()
def create(proposal_no: int):
    """Create a new entry for a proposal with the given number."""
    proposal = service.create_proposal(proposal_no)
    typer.echo(proposal)


@app.command()
def list():
    """List all proposal entries."""
    proposals = service.list_proposals()
    typer.echo(proposals)


if __name__ == "__main__":
    app()
