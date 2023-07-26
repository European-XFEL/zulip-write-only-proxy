from pathlib import Path
from .repository import ProposalRepository
from .model import Proposal

REPOSITORY = ProposalRepository(path=Path(__file__).parent / "proposals.json")


def create_proposal(proposal_no: int) -> Proposal:
    proposal = Proposal.create(proposal_no)
    REPOSITORY.put(proposal)
    return proposal


def get_proposal(token: str) -> Proposal:
    return REPOSITORY.get(token)


def list_proposals() -> list[Proposal]:
    return REPOSITORY.list()
