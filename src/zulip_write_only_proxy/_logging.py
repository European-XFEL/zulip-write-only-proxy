import inspect
import logging
import sys
from typing import TYPE_CHECKING, List

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.stdlib import ProcessorFormatter
from structlog.types import Processor

from .settings import settings

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response


def get_logger():
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    module_name = module.__name__ if module else __package__
    return structlog.get_logger(logger_name=module_name.replace(f"{__package__}.", "."))


if settings.debug:
    level = logging.DEBUG
    renderer = structlog.dev.ConsoleRenderer()
    # sentry_processor = sentry.SentryProcessor(level=logging.INFO)
else:
    level = logging.INFO
    renderer = structlog.processors.JSONRenderer(indent=1)
    # sentry_processor = sentry.SentryJsonProcessor(level=logging.WARNING)

shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.StackInfoRenderer(),
    structlog.dev.set_exc_info,
    # structlog.processors.CallsiteParameterAdder(
    #     {
    #         structlog.processors.CallsiteParameter.FILENAME,
    #         structlog.processors.CallsiteParameter.LINENO,
    #     }
    # ),
    structlog.processors.TimeStamper(fmt="%Y-%m-%dT%H:%M:%SZ", utc=True),
]

structlog_processors = shared_processors + [renderer]
logging_processors: List[Processor] = [
    ProcessorFormatter.remove_processors_meta,
    renderer,
]

# if sentry.SENTRY_ENABLED:
#     processors.append(sentry_processor)

formatter = ProcessorFormatter(
    # These run ONLY on `logging` entries that do NOT originate within structlog
    foreign_pre_chain=shared_processors,
    # These run on ALL entries after the pre_chain is done
    processors=logging_processors,
)


def configure() -> None:
    """
    Configures logging and sets up Uvicorn to use Structlog.
    """
    structlog.configure(
        processors=structlog_processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
        cache_logger_on_first_use=True,
        context_class=dict,
    )

    log = structlog.get_logger(logger_name=__name__.replace("kourou.", "."))

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logging.basicConfig(handlers=[handler], level=logging.INFO)

    configure_uvicorn()

    log.info("Configured Logging")


def configure_uvicorn():
    import uvicorn.config

    uvicorn.config.LOGGING_CONFIG["formatters"]["default"] = {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": renderer,
        "foreign_pre_chain": shared_processors,
    }

    uvicorn.config.LOGGING_CONFIG["handlers"]["default"] = {
        "class": "logging.StreamHandler",
        "formatter": "default",
    }

    uvicorn.config.LOGGING_CONFIG["root"] = {
        "level": logging.INFO,
        "handlers": ["default"],
    }

    # Disabled access log handlers as they are handled by the middleware
    uvicorn.config.LOGGING_CONFIG["loggers"]["uvicorn.access"]["handlers"] = []


class RequestLoggingMiddleware(BaseHTTPMiddleware):

    log = structlog.get_logger(logger_name="uvicorn.access")

    async def dispatch(self, request: "Request", call_next) -> "Response":
        """Add a middleware to FastAPI that will log requests and responses,
        this is used instead of the builtin Uvicorn access logging to better
        integrate with structlog"""
        info = {
            "method": request.method,
            "path": request.url.path,
            "client": request.client,
        }

        if request.query_params:
            info["query_params"] = request.query_params

        if request.path_params:
            info["path_params"] = request.path_params

        self.log.debug("Request", **info)
        response = await call_next(request)
        if response.status_code < 400:
            self.log.debug("Response", status_code=response.status_code)
        elif response.status_code < 500:
            self.log.info("Response", status_code=response.status_code)
        else:
            self.log.error("Response", status_code=response.status_code)
        return response
