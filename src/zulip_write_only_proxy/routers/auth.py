import fastapi
from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from fastapi import Request
from fastapi.responses import RedirectResponse

from zulip_write_only_proxy.settings import settings

router = fastapi.APIRouter(prefix="/oauth", include_in_schema=False)

_oauth = OAuth()

_oauth.register(
    name="dadev",
    client_id=settings.auth.client_id,
    client_secret=settings.auth.client_secret.get_secret_value(),
    server_metadata_url=str(settings.auth.server_metadata_url),
)

oauth: StarletteOAuth2App = _oauth.dadev  # type: ignore


@router.get("/")
async def auth(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url=request.scope.get("root_path") or "/")
    url = request.url_for("callback")
    url = url.replace(path=f"{request.scope.get('root_path') or ''}{url.path}")
    return await oauth.authorize_redirect(request, url)


@router.get("/callback")
async def callback(request: Request):
    token = await oauth.authorize_access_token(request)
    user = await oauth.userinfo(token=token)

    request.session["user"] = dict(user)

    return RedirectResponse(url=request.scope.get("root_path") or "/")


@router.get("/logout")
def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url=request.scope.get("root_path") or "/")
