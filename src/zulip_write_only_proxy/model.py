import secrets
from typing import Self

from pydantic import BaseModel


class Proposal(BaseModel):
    token: str
    proposal_no: int
    stream: str
    topic: str

    @classmethod
    def create(cls, proposal_no: int) -> Self:
        return cls(
            token=secrets.token_urlsafe(),
            proposal_no=proposal_no,
            stream=f"some-pattern-{proposal_no}",
            topic=f"some-pattern-{proposal_no}",
        )
