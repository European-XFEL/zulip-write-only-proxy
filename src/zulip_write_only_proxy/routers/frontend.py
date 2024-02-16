from pathlib import Path
from typing import TYPE_CHECKING

import fastapi
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .. import exceptions, logger, models, services

if TYPE_CHECKING:
    from ..settings import Settings

TEMPLATES: Jinja2Templates = None  # type: ignore[assignment]


def configure(_: "Settings", app: fastapi.FastAPI):
    global TEMPLATES
    frontend_dir = Path(__file__).parent.parent / "frontend"

    static_dir = frontend_dir / "static"
    templates_dir = frontend_dir / "templates"

    logger.info("Mounting static files", directory=static_dir.relative_to(Path.cwd()))
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    logger.info(
        "Setting Jinja2 Templates", directory=templates_dir.relative_to(Path.cwd())
    )
    TEMPLATES = Jinja2Templates(directory=templates_dir)


class AuthException(exceptions.ZwopException):
    pass


async def check_auth(request: Request):
    user = request.session.get("user")
    if not user:
        raise AuthException(
            status_code=401,
            detail=(
                "Unauthorized - no authentication provided"
                if request.url.path.rstrip("/") != request.scope.get("root_path", "")
                else ""
            ),
        )

    if "da" not in user.get("groups", []):
        raise AuthException(
            status_code=403,
            detail=f"Forbidden - `{user.get('preferred_username')}` not allowed access",
        )


async def auth_redirect(request: Request, exc: AuthException):
    logger.info("Redirecting to login", status_code=exc.status_code, detail=exc.detail)
    return TEMPLATES.TemplateResponse(
        "login.html",
        {"request": request, "message": exc.detail},
        headers={
            "HX-Retarget": "#content",
            "HX-Reselect": "#content",
            "HX-Swap": "outerHTML",
        },
        status_code=exc.status_code,
    )


router = fastapi.APIRouter(
    dependencies=[fastapi.Depends(check_auth)], include_in_schema=False
)


@router.get("/")
def root(request: Request):
    return client_list(request)


@router.get("/client/list")
def client_list(request: Request):
    clients = services.list_clients()
    clients.reverse()
    return TEMPLATES.TemplateResponse(
        "list.html",
        {"request": request, "clients": clients},
        headers={
            "HX-Retarget": "#content",
            "HX-Reselect": "#content",
            "HX-Swap": "outerHTML",
        },
    )


@router.get("/client/create")
def client_create(request: Request):
    schema = models.ScopedClientCreate.model_json_schema()
    optional = schema["properties"]
    required = {field: optional.pop(field) for field in schema["required"]}
    return TEMPLATES.TemplateResponse(
        "create.html",
        {"request": request, "required": required, "optional": optional},
    )


@router.post("/client/create")
async def client_create_post(request: Request):
    user = request.session.get("user", {})
    try:
        new_client = models.ScopedClientCreate(**request.query_params)  # type: ignore[arg-type]
        client = await services.create_client(
            new_client, created_by=user.get("email", "none")
        )
        dump = client.model_dump()
        dump["key"] = client.key.get_secret_value()
        bot = services.get_bot(client.bot_name)
        return TEMPLATES.TemplateResponse(
            "fragments/create-success.html",
            {
                "request": request,
                "client": models.ScopedClientWithKey(**dump),
                "bot_url": bot.base_url,
            },
        )
    except Exception as e:
        return TEMPLATES.TemplateResponse(
            "fragments/alert-error.html",
            {"request": request, "message": e.__repr__()},
        )
