import logging
import sys
from typing import TYPE_CHECKING, Sequence

import colorama
import structlog
import structlog.typing
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.stdlib import ProcessorFormatter

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response


def parameter_parser(logger, method_name, event_dict):
    event_dict["logger_name"] = ".".join(
        [event_dict.pop("module", None), event_dict.pop("func_name", None)]
    )
    return event_dict


def configure(debug: bool) -> None:
    """
    Configures logging and sets up Uvicorn to use Structlog.
    """

    level = logging.DEBUG if debug else logging.INFO
    level_styles = structlog.dev.ConsoleRenderer.get_default_level_styles()

    if debug:
        level_styles["debug"] = colorama.Fore.MAGENTA

    renderer: structlog.typing.Processor = (
        structlog.dev.ConsoleRenderer(colors=True, level_styles=level_styles)  # type: ignore[assignment]
        if debug
        else structlog.processors.JSONRenderer(indent=1)
    )

    # sentry_processor = sentry.SentryProcessor(level=level)

    shared_processors: Sequence[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%dT%H:%M:%SZ", utc=True),
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.MODULE,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            }
        ),
        parameter_parser,
    ]

    structlog_processors = [*shared_processors, renderer]
    logging_processors = [ProcessorFormatter.remove_processors_meta, renderer]

    # if sentry.SENTRY_ENABLED:
    #     processors.append(sentry_processor)

    formatter = ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=logging_processors,
    )

    structlog.configure(
        processors=structlog_processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
        cache_logger_on_first_use=True,
        context_class=dict,
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logging.basicConfig(handlers=[handler], level=logging.INFO)

    configure_uvicorn(renderer, shared_processors)

    log = structlog.get_logger()
    log.info("Configured Logging")


def configure_uvicorn(renderer, shared_processors):
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
    log = structlog.get_logger()

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
            info["query_params"] = str(request.query_params)

        if request.path_params:
            info["path_params"] = str(request.path_params)

        self.log.debug("Request", **info)
        response = await call_next(request)
        if response.status_code < 400:
            self.log.debug("Response", status_code=response.status_code)
        elif response.status_code < 500:
            self.log.info("Response", status_code=response.status_code)
        else:
            self.log.error("Response", status_code=response.status_code)
        return response
