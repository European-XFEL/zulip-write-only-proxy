from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

TokenKind = Literal["zulip", "mymdc"]


class FileWriteRequest(BaseModel):
    proposal_no: int = Field(ge=1)
    kind: TokenKind
    key: str = Field(min_length=1)
    zwop_url: HttpUrl
    overwrite: bool = False
    dry_run: bool = False


class FileWriteResult(BaseModel):
    kind: TokenKind
    target: str
    status_code: int
    msg: str


class FileWriteSummary(BaseModel):
    proposal: int
    results: list[FileWriteResult]
    status_code: int


class ErrorResponse(BaseModel):
    msg: str
    status_code: int
    details: dict[str, str | int | bool] = Field(default_factory=dict)
