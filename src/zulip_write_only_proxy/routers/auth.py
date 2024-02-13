from typing import TYPE_CHECKING

import fastapi
from authlib.integrations.starlette_client import (  # type: ignore[import-untyped]
    OAuth,
    StarletteOAuth2App,
)
from fastapi import Request
from fastapi.responses import RedirectResponse

from .. import logger

if TYPE_CHECKING:
    from fastapi import FastAPI

    from ..settings import Settings


router = fastapi.APIRouter(prefix="/oauth", include_in_schema=False)

_OAUTH = OAuth()

OAUTH: StarletteOAuth2App = None  # type: ignore[assignment]


def configure(settings: "Settings", _: "FastAPI") -> None:
    global OAUTH

    logger.info("Configuring OAuth", settings_auth=settings.auth)

    _OAUTH.register(
        name="dadev",
        client_id=settings.auth.client_id,
        client_secret=settings.auth.client_secret.get_secret_value(),
        server_metadata_url=str(settings.auth.server_metadata_url),
    )

    OAUTH = _OAUTH.dadev  # type: ignore[assignment, no-redef]


@router.get("/")
async def auth(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url=request.scope.get("root_path") or "/")
    url = request.url_for("callback")
    url = url.replace(path=f"{request.scope.get('root_path') or ''}{url.path}")
    return await OAUTH.authorize_redirect(request, url)


@router.get("/callback")
async def callback(request: Request):
    token = await OAUTH.authorize_access_token(request)
    user = await OAUTH.userinfo(token=token)

    request.session["user"] = dict(user)

    return RedirectResponse(url=request.scope.get("root_path") or "/")


@router.get("/logout")
def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url=request.scope.get("root_path") or "/")
