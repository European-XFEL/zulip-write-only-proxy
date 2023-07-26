import typer
import uvicorn

from . import service

app = typer.Typer()


@app.command()
def create(proposal_no: int):
    """Create a new scoped client for a proposal."""
    proposal = service.create_proposal(proposal_no)
    typer.echo(proposal)


@app.command()
def list():
    """List all scoped clients."""
    proposals = service.list_proposals()
    typer.echo(proposals)


if __name__ == "__main__":
    app()
