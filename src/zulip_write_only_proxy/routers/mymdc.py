from typing import Annotated

import orjson
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .. import logger, models, mymdc
from .api import get_client

ScopedClient = Annotated[models.ScopedClient, Depends(get_client)]


async def proxy_request(mymdc_path: str, params) -> Response:
    res = await mymdc.CLIENT.get(mymdc_path, params=params)

    return Response(
        content=res.content,
        media_type=res.headers["Content-Type"],
        headers=res.headers,
        status_code=res.status_code,
    )


async def check_and_proxy_request(
    request: Request,
    client: ScopedClient,
    req_proposal_no: int | None,
    mymdc_path: str,
    params: dict,
) -> Response:
    params = {k: v for k, v in params.items() if v is not None}

    if request.query_params.keys() != params.keys():
        logger.warning(
            "Dropped query parameters",
            keys=set(request.query_params.keys()) - set(params.keys()),
        )

    if req_proposal_no and int(req_proposal_no) != client.proposal_no:
        raise HTTPException(
            status_code=403, detail="Client not scoped to this proposal"
        )

    res = await proxy_request(mymdc_path, params)
    content = orjson.loads(res.body)

    # Use first item if content is a list, e.g. for paginated responses
    if isinstance(content, list):
        content = content[0]

    res_proposal_id = (
        content.get("proposal_id")
        or content.get("experiment", {}).get("proposal_id")
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


@router.get("/proposals/by_number/{proposal_no}")
async def get_proposals_by_number(
    request: Request, client: ScopedClient, proposal_no: int
):
    return await check_and_proxy_request(
        request, client, proposal_no, f"/api/proposals/by_number/{proposal_no}", {}
    )


@router.get("/runs/runs_by_proposal")
@router.get("/samples/")
@router.get("/proposals/by_number/{proposal_no}/runs")
async def get_proposals_by_number_runs(
    request: Request,
    client: ScopedClient,
    proposal_no: int,
    page_size: int | None = None,
    page: int | None = None,
):
    return await check_and_proxy_request(
        request,
        client,
        proposal_no,
        request.scope["path"].replace("/api/mymdc", "/api"),
        {"page_size": page_size, "page": page, "proposal_number": proposal_no},
    )


@router.get("/proposals/by_number/{proposal_no}/runs/{run_number}")
async def get_proposals_runs(
    request: Request, client: ScopedClient, proposal_no: int, run_number: int
):
    return await check_and_proxy_request(
        request,
        client,
        proposal_no,
        f"/api/proposals/by_number/{proposal_no}/runs/{run_number}",
        {},
    )


@router.get("/samples/{id}")
@router.get("/experiments/{id}")
@router.get("/runs/{id}")
async def get_with_id(request: Request, client: ScopedClient, id: int):
    return await check_and_proxy_request(
        request,
        client,
        client.proposal_no,
        request.scope["path"].replace("/api/mymdc", "/api"),
        {},
    )
