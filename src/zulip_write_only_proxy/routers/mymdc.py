from typing import Annotated, TypeAlias

import orjson
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .. import models, mymdc
from .api import get_client

ScopedClient: TypeAlias = Annotated[models.ScopedClient, Depends(get_client)]


async def proxy_request(request: Request) -> Response:
    path = request.scope["path"].replace("/api/mymdc", "/api")  # rewrite path for mymdc

    res = await mymdc.CLIENT.get(path)

    return Response(
        content=res.content,
        media_type=res.headers["Content-Type"],
        headers=res.headers,
        status_code=res.status_code,
    )


async def check_and_proxy_request(client: ScopedClient, request: Request) -> Response:
    req_proposal_no = request.path_params.get("proposal_no")
    if req_proposal_no and int(req_proposal_no) != client.proposal_no:
        raise HTTPException(
            status_code=403, detail="Client not scoped to this proposal"
        )

    res = await proxy_request(request)
    content = orjson.loads(res.body)

    res_proposal_id = (
        content.get("proposal_id")
        or content.get("proposal", {}).get("id")
        or content.get("id")
    )

    res_proposal_no = content.get("proposal", {}).get("no") or content.get("id")

    if all(n is None for n in (res_proposal_id, res_proposal_no)):
        raise HTTPException(
            status_code=400, detail="Cannot determine proposal for response"
        )

    if any((
        res_proposal_id == client.proposal_id,
        res_proposal_no == client.proposal_no,
    )):
        return res

    raise HTTPException(status_code=403, detail="Client not scoped to this proposal")


router = APIRouter(prefix="/api/mymdc", tags=["mymdc"])


@router.get("/proposals/by_number/{proposal_no}/runs")
@router.get("/proposals/by_number/{proposal_no}")
async def get_proposals_by_number(
    proposal_no: int, res=Depends(check_and_proxy_request)
):
    return res


@router.get("/proposals/by_number/{proposal_no}/runs/{run_number}")
async def get_proposals_runs(
    proposal_no: int, run_number: int, res=Depends(check_and_proxy_request)
):
    return res


@router.get("/samples/{id}")
@router.get("/experiments/{id}")
async def get(id: int, res=Depends(check_and_proxy_request)):
    return res
