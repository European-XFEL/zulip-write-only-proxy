import typer

from . import service

app = typer.Typer()


@app.command()
def create(proposal_no: int):
    proposal = service.create_proposal(proposal_no)
    typer.echo(proposal)


@app.command()
def list():
    proposals = service.list_proposals()
    typer.echo(proposals)


if __name__ == "__main__":
    app()
