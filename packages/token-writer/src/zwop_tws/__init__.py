__version__: str
__version_tuple__: tuple[int | str, ...]

try:
    from ._version import (  # pyright: ignore[reportMissingImports]
        __version__,
        __version_tuple__,
    )
except ImportError:  # pragma: no cover
    __version__ = "unknown"
    __version_tuple__ = (0, 0, 0)  # type: ignore[assignment]


from .models import FileWriteRequest, FileWriteResult, FileWriteSummary

__all__ = [
    "FileWriteRequest",
    "FileWriteResult",
    "FileWriteSummary",
    "__version__",
    "__version_tuple__",
]
