try:
    from ._version import __version__, __version_tuple__
except ImportError:
    __version__ = "unknown"
    __version_tuple__ = (0, 0, 0)  # type: ignore[assignment]

from structlog import get_logger

from . import _logging
from .settings import settings

_logging.configure(settings.debug)

logger = get_logger()

__all__ = ["__version__", "__version_tuple__", "logger"]
