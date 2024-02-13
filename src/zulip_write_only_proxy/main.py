from __future__ import annotations

from contextlib import asynccontextmanager

import fastapi
from starlette.middleware.sessions import SessionMiddleware

from . import logger, routers, services
from ._logging import RequestLoggingMiddleware
from .settings import settings


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    from . import mymdc

    services.configure(settings, app)

    mymdc.configure(settings, app)

    for module in [routers.api, routers.auth, routers.frontend]:
        app.include_router(module.router)

        if hasattr(module, "configure"):
            module.configure(settings, app)

    yield


app = fastapi.FastAPI(
    title="Zulip Write Only Proxy",
    lifespan=lifespan,
    exception_handlers={
        routers.frontend.AuthException: routers.frontend.auth_redirect,
    },
)


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret.get_secret_value(),
)

app.add_middleware(RequestLoggingMiddleware)

if __name__ == "__main__":
    import uvicorn

    logger.info(
        "Starting uvicorn",
        app=f"{__package__}.main:app",
        port=settings.address.port or 8000,
        log_level=settings.log_level,
        host=settings.address.host or "127.0.0.1",
        proxy_headers=True,
        reload=False,
        root_path=settings.proxy_root_path,
    )

    uvicorn.run(
        app=f"{__package__}.main:app",
        port=settings.address.port or 8000,
        log_level=settings.log_level,
        host=settings.address.host or "127.0.0.1",
        proxy_headers=True,
        # reload=settings.debug,
        reload=False,
        root_path=settings.proxy_root_path,
    )
