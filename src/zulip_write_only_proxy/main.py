def create_app():
    from contextlib import asynccontextmanager

    import fastapi
    from starlette.middleware.sessions import SessionMiddleware

    from . import routers, services
    from ._logging import RequestLoggingMiddleware
    from .settings import settings

    @asynccontextmanager
    async def lifespan(app: fastapi.FastAPI):
        from . import _logging, mymdc

        _logging.configure(debug=app.debug, add_call_site_parameters=True)

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
        debug=settings.debug,
        exception_handlers={
            routers.frontend.AuthException: routers.frontend.auth_redirect,
        },
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret.get_secret_value(),
    )

    app.add_middleware(RequestLoggingMiddleware)

    return app


if __name__ == "__main__":
    import uvicorn

    from . import _logging, get_logger
    from .settings import settings

    _logging.configure(settings.debug, add_call_site_parameters=False)

    logger = get_logger()

    args = {
        "app": f"{__package__}.main:create_app",
        "host": settings.address.host or "127.0.0.1",
        "port": settings.address.port or 8000,
        "reload": settings.debug,
        "log_level": settings.log_level,
        "root_path": settings.proxy_root,
        "factory": True,
    }

    logger.info("Starting uvicorn", **args)

    uvicorn.run(**args)
