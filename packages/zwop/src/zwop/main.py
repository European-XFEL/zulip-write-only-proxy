from contextlib import asynccontextmanager
from pathlib import Path

import fastapi
import uvicorn
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import _logging, get_logger, routers
from ._logging import RequestLoggingMiddleware
from .mymdc import configure as configure_mymdc
from .services import configure as configure_services
from .settings import configure as configure_settings


def create_app():
    settings = configure_settings()

    @asynccontextmanager
    async def lifespan(app: fastapi.FastAPI):
        _logging.configure(debug=app.debug, add_call_site_parameters=True)

        app.state.settings = settings

        await configure_services(app)

        await configure_mymdc(app)

        frontend_dir = Path(__file__).parent / "frontend"
        app.mount(
            "/static",
            StaticFiles(directory=frontend_dir / "static"),
            name="static",
        )
        app.state.templates = Jinja2Templates(directory=frontend_dir / "templates")

        for module in [routers.api, routers.auth, routers.frontend, routers.mymdc]:
            app.include_router(module.router)

        yield

        await app.state.tws_client.aclose()

    app = fastapi.FastAPI(
        title="Zulip Write Only Proxy",
        lifespan=lifespan,
        debug=settings.debug,
        root_path=settings.proxy_root,
        exception_handlers={
            routers.frontend.AuthException: routers.frontend.auth_redirect,
        },
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret.get_secret_value(),
    )

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    return app


def main():
    settings = configure_settings()

    _logging.configure(settings.debug, add_call_site_parameters=False)

    logger = get_logger()

    logger.info(
        "Proxy settings",
        proxy_root=settings.proxy_root,
        proxy_headers=settings.proxy_headers,
        forwarded_allow_ips=settings.forwarded_allow_ips,
    )

    host = settings.address.host or "127.0.0.1"

    if "127.0.0.1" in host:
        logger.critical(
            "Running on localhost. This is only accessible from the local machine."
        )

    uvicorn.run(
        app=f"{__package__}.main:create_app",
        host=settings.address.host or "127.0.0.1",
        port=settings.address.port or 8000,
        reload=settings.debug,
        log_level=settings.log_level,
        root_path=settings.proxy_root,
        proxy_headers=settings.proxy_headers,
        forwarded_allow_ips=settings.forwarded_allow_ips,
        factory=True,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
