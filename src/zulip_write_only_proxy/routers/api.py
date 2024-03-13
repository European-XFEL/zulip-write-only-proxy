from typing import TYPE_CHECKING, Annotated

import fastapi
import orjson
from fastapi.security import APIKeyHeader

from zulip_write_only_proxy import mymdc

from .. import __version__, __version_tuple__, logger, models, services

if TYPE_CHECKING:
    from tempfile import SpooledTemporaryFile

_docs_url = "https://zulip.com/api/send-message#response"

router = fastapi.APIRouter(prefix="/api")

api_key_header = APIKeyHeader(name="X-API-key", auto_error=False)


async def get_client(
    key: Annotated[str, fastapi.Security(api_key_header)],
) -> models.ScopedClient:
    return await services.get_client(key)


@router.post(
    "/send_message",
    response_description=f"See <a href='{_docs_url}'>{_docs_url}</a>",
    tags=["zulip"],
)
def send_message(
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
    topic: Annotated[str, fastapi.Query(...)],
    content: Annotated[str, fastapi.Body(...)],
    image: Annotated[fastapi.UploadFile | None, fastapi.File()] = None,
):
    if image:
        # Some screwing around to get the spooled tmp file to act more like a real file
        # since Zulip needs it to have a filename
        f: "SpooledTemporaryFile" = image.file  # type: ignore[assignment]
        f._file.name = image.filename  # type: ignore[misc, assignment]

        result = client.upload_file(f)

        content += f"\n[]({result['uri']})"

    return client.send_message(topic, content)


_docs_url = "https://zulip.com/api/update-message#response"


@router.patch(
    "/update_message",
    response_description=f"See <a href='{_docs_url}'>{_docs_url}</a>",
    tags=["zulip"],
)
def update_message(
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
    message_id: Annotated[int, fastapi.Query(...)],
    propagate_mode: Annotated[models.PropagateMode | None, fastapi.Query()] = None,
    content: Annotated[str | None, fastapi.Body(media_type="text/plain")] = None,
    topic: Annotated[str | None, fastapi.Query()] = None,
):
    if not (content or topic):  # sourcery skip
        raise fastapi.HTTPException(
            status_code=400,
            detail=(
                "Either content (update message text) or topic (rename message topic) "
                "must be provided"
            ),
        )
    return client.update_message(topic, content, message_id, propagate_mode)


_docs_url = "https://zulip.com/api/upload-file#response"


@router.post(
    "/upload_file",
    response_description=f"See <a href='{_docs_url}'>{_docs_url}</a>",
    tags=["zulip"],
)
def upload_file(
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
    file: Annotated[fastapi.UploadFile, fastapi.File(...)],
):
    f: "SpooledTemporaryFile" = file.file  # type: ignore[assignment]
    f._file.name = file.filename  # type: ignore[misc, assignment]

    return client.upload_file(f)


_docs_url = "https://zulip.com/api/get-stream-topics#response"


@router.get(
    "/get_stream_topics",
    response_description=f"See <a href='{_docs_url}'>{_docs_url}</a>",
    tags=["zulip"],
)
def get_stream_topics(
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
):
    return client.get_stream_topics()


mymdc_proxy_routes = {
    "proposals/by_number/{proposal_no}": ["", "runs", "runs/{run_number}"],
    "sample_types": ["{id}"],
    "samples": ["", "{id}"],
    "experiments": ["", "{id}"],
}


async def get_mymdc(
    request: fastapi.Request,
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
    proposal_no: int | None = None,
    run_number: int | None = None,
    id: int | None = None,
):
    logger.debug("get_mymdc", proposal_no=proposal_no, run_number=run_number, id=id)
    # Early exit if proposal_no is explicitly provided and does not match client
    if proposal_no and proposal_no != client.proposal_no:
        raise fastapi.HTTPException(
            status_code=403,
            detail=f"Client is scoped to {client.proposal_no=}, not {proposal_no=}",
        )

    res = await mymdc.CLIENT.get(
        request.scope["path"].replace("/api/mymdc", "/api")  # rewrite path for mymdc
    )

    # Error response or proposal_no provided and previously checked
    if res.status_code != 200 or proposal_no:
        return _create_response(res)

    res_dict = orjson.loads(res.content)

    checks = [
        _check_prefix_path(res_dict, client),
        await _check_proposal_id(res_dict, client),
    ]

    # Any checks true? Return response
    if any(checks):
        return _create_response(res)

    # All checks are None? No checks performed
    if all(c is None for c in checks):
        logger.error(
            "No checks performed", res=res, client=client, proposal_no=proposal_no
        )
        raise fastapi.HTTPException(
            status_code=500,
            detail="No checks could be performed",
        )

    # All checks are False? Raise 403
    raise fastapi.HTTPException(
        status_code=403,
        detail="No checks passed",
    )


def _create_response(res):
    return fastapi.Response(
        content=res.content,
        media_type=res.headers["Content-Type"],
        headers=res.headers,
        status_code=res.status_code,
    )


def _check_prefix_path(res_dict, client):
    if v := res_dict.get("first_prefix_path"):
        return v in f"/p{client.proposal_no:06d}/"
    return None


async def _check_proposal_id(res_dict, client):
    if v := res_dict.get("proposal_id"):
        proposal_no = orjson.loads(
            (await mymdc.CLIENT.get(f"/api/proposals/{v}")).content
        ).get("number")
        return proposal_no == client.proposal_no
    return None


for path, subpaths in mymdc_proxy_routes.items():
    for subpath in subpaths:
        get_mymdc = router.get(
            "/" + "/".join(["mymdc", path, subpath]).strip("/"),
            tags=["mymdc"],
            name="",
            response_class=fastapi.Response,
        )(get_mymdc)


@router.get("/me", response_model_exclude={"key"})
def get_me(
    client: Annotated[models.ScopedClient, fastapi.Depends(get_client)],
) -> models.ScopedClient:
    return client


@router.get("/health")
def healthcheck(request: fastapi.Request):
    return {
        "status": "OK",
        "dirty": "dirty" in __version__,
        "dev": "+" in __version__,
        "version": __version__,
        "version_tuple": __version_tuple__,
        "root_path": request.scope.get("root_path"),
    }
