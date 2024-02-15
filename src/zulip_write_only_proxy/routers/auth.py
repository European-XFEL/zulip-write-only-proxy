from typing import TYPE_CHECKING

import fastapi
from authlib.integrations.starlette_client import (  # type: ignore[import-untyped]
    OAuth,
    OAuthError,
    StarletteOAuth2App,
)
from fastapi import Request
from fastapi.responses import RedirectResponse

from .. import logger
from .frontend import AuthException

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
        return RedirectResponse(url=request.base_url)
    return await OAUTH.authorize_redirect(request, request.url_for("callback"))


@router.get("/callback")
async def callback(request: Request):
    try:
        token = await OAUTH.authorize_access_token(request)
        user = await OAUTH.userinfo(token=token)
    except OAuthError as e:
        await logger.aerror("OAuth error", error=str(e))
        raise AuthException(status_code=401, detail=str(e)) from e

    request.session["user"] = dict(user)

    await logger.ainfo("Logged in", username=user["preferred_username"])

    return RedirectResponse(url=request.base_url)


@router.get("/logout")
async def logout(request: Request):
    if user := request.session.pop("user", None):
        await logger.ainfo("Logged out", username=user["preferred_username"])
    return RedirectResponse(url=request.base_url)
