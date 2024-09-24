def create_app():
    from contextlib import asynccontextmanager

    import fastapi
    from fastapi.middleware.gzip import GZipMiddleware
    from starlette.middleware.sessions import SessionMiddleware

    from . import routers, services
    from ._logging import RequestLoggingMiddleware
    from .settings import settings

    @asynccontextmanager
    async def lifespan(app: fastapi.FastAPI):
        from . import _logging, mymdc

        _logging.configure(debug=app.debug, add_call_site_parameters=True)

        await services.configure(settings, app)

        mymdc.configure(settings, app)

        for module in [routers.api, routers.auth, routers.frontend, routers.mymdc]:
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
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    return app


def get_trusted_hosts(logger):  # pragma: no cover
    import socket
    import struct
    from pathlib import Path

    trusted = set()

    routes = Path("/proc/net/route").read_text()
    lines = routes.split("\n")
    for route in lines[1:-1]:
        fields = route.strip().split()
        if not fields or fields[1] != "00000000" or not int(fields[3], 16) & 2:
            # Skip non-default routes
            logger.debug("Route is not default, skipping", route=route)
            continue

        if gateway := socket.inet_ntoa(struct.pack("<L", int(fields[2], 16))):
            logger.info("Found gateway", gateway=gateway)
            trusted.add(gateway)

    if not trusted:
        logger.warning("No gateways found in /proc/net/route", routes=routes)

    try:
        traefik = socket.gethostbyname_ex("traefik")
        trusted |= set(traefik[2])
        logger.info("Resolved traefik", traefik=traefik)
    except socket.gaierror:
        logger.warning("Failed to resolve traefik")

    if not trusted:
        logger.critical("No trusted hosts found")

    return list(trusted)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    from . import _logging, get_logger
    from .settings import settings

    _logging.configure(settings.debug, add_call_site_parameters=False)

    logger = get_logger()

    trusted_hosts = None
    if settings.proxy_root and settings.proxy_root != "/":
        trusted_hosts = get_trusted_hosts(logger)

    logger.info("Trusted hosts", trusted_hosts=trusted_hosts)

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
        forwarded_allow_ips=trusted_hosts,
        factory=True,
    )
