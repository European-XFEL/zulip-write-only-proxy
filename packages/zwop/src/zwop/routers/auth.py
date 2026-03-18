import fastapi
from authlib.integrations.starlette_client import (  # type: ignore[import-untyped]
    OAuthError,
    StarletteOAuth2App,
)
from fastapi import Request
from fastapi.responses import RedirectResponse

from .. import logger
from .frontend import AuthException

router = fastapi.APIRouter(prefix="/oauth", include_in_schema=False)


@router.get("/")
async def auth(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url=request.base_url)
    oauth: StarletteOAuth2App = request.app.state.oauth
    return await oauth.authorize_redirect(request, request.url_for("callback"))


@router.get("/callback")
async def callback(request: Request):
    oauth: StarletteOAuth2App = request.app.state.oauth
    try:
        token = await oauth.authorize_access_token(request)
        user = await oauth.userinfo(token=token)
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
