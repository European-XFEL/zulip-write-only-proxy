from pathlib import Path
from typing import TYPE_CHECKING

import fastapi
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .. import exceptions, logger, models, services

if TYPE_CHECKING:  # pragma: no-cover
    from ..settings import Settings

TEMPLATES: Jinja2Templates = None  # type: ignore[assignment]


def configure(settings: "Settings", app: fastapi.FastAPI):
    global TEMPLATES
    frontend_dir = Path(__file__).parent.parent / "frontend"
    static_dir = frontend_dir / "static"
    templates_dir = frontend_dir / "templates"

    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    TEMPLATES = Jinja2Templates(directory=templates_dir)

    static_files = {"static_main_css": "main.css", "static_htmx": "htmx.min.js"}

    for key, path in static_files.items():
        TEMPLATES.env.globals[key] = settings.proxy_root + app.url_path_for(  # pyright: ignore[reportInvalidTypeForm]
            "static", path=path
        )

    logger.info(
        "Configured static files and Jinja2 templates",
        static_dir=static_dir.relative_to(Path.cwd()),
        templates_dir=templates_dir.relative_to(Path.cwd()),
        env=TEMPLATES.env.globals,
    )


class AuthException(exceptions.ZwopException):
    pass


async def check_auth(request: Request):  # noqa: RUF029
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

    logger.debug("Authenticated", user=user)


async def auth_redirect(request: Request, exc: AuthException):  # noqa: RUF029
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


@router.get("/client/list")
@router.get("/", name="root")
async def client_list(request: Request):
    if request.headers.get("HX-Current-URL", "").endswith("/client/list"):
        clients = await services.list_clients()
        return TEMPLATES.TemplateResponse(
            "fragments/list-table-rows.html",
            {"request": request, "clients": clients},
            headers={"HX-Retarget": "#rows"},
        )

    return TEMPLATES.TemplateResponse(
        "list.html",
        {"request": request},
        headers={"HX-Replace-Url": str(request.url_for("client_list"))},
    )


@router.get("/client/create")
async def client_create(request: Request):
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
        dump["token"] = client.token.get_secret_value()
        bot = await services.get_bot(client._bot_key)

        if bot is None:
            logger.warning("Bot not found")

        return TEMPLATES.TemplateResponse(
            "fragments/create-success.html",
            {
                "request": request,
                "client": models.ScopedClientWithToken(**dump),
                "bot_site": bot.site if bot else None,
            },
        )
    except exceptions.ZwopException as e:
        logger.warning("Could not create client", exc_info=e)
        return TEMPLATES.TemplateResponse(
            "fragments/alert.html",
            {"request": request, "message": e.detail, "level": "error"},
        )
    except Exception as e:
        logger.error("Error creating client", exc_info=e)
        return TEMPLATES.TemplateResponse(
            "fragments/alert.html",
            {"request": request, "message": e.__repr__(), "level": "error"},
        )


@router.delete("/client/")
async def client_delete(request: Request):
    client_key = request.headers.get("X-API-Key")

    if not client_key:
        raise exceptions.ZwopException(
            status_code=400,
            detail="Bad Request - missing X-API-Key header",
        )

    try:
        deleted = await services.delete_client(client_key)
        return JSONResponse({"detail": f"Deleted {deleted}"})
    except KeyError as e:
        raise exceptions.ZwopException(
            status_code=404,
            detail=f"Client not found {e}",
        ) from e
    except Exception as e:
        raise exceptions.ZwopException(
            status_code=500,
            detail=f"{e.__repr__()}",
        ) from e


@router.get("/client/messages")
async def client_messages(request: Request):
    client_key = request.headers.get("X-API-Key")
    if not client_key:
        raise exceptions.ZwopException(
            status_code=400,
            detail="Bad Request - missing X-API-Key header",
        )
    client = await services.get_client(client_key)

    if request.headers.get("HX-Current-URL", "").endswith("/client/messages"):
        _messages = client.get_messages()
        if messages := [
            models.Message(
                topic=m["subject"],
                id=m["id"],
                content=m["content"],
                timestamp=m["timestamp"],
            )
            for m in _messages["messages"]
        ]:
            return TEMPLATES.TemplateResponse(
                "fragments/list-messages-rows.html",
                {"request": request, "messages": messages},
                headers={"HX-Retarget": "#rows"},
            )

        return TEMPLATES.TemplateResponse(
            "fragments/alert.html",
            {
                "request": request,
                "message": (
                    f"No messages found for {client.stream} on {client.bot_site} by "
                    f"bot ID {client.bot_id}"
                ),
                "level": "warning",
            },
            headers={"HX-Reswap": "afterend", "HX-Retarget": "#table"},
        )

    return TEMPLATES.TemplateResponse(
        "messages.html",
        {"request": request, "client": client},
        headers={"HX-Retarget": "#content"},
    )
