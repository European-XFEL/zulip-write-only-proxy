try:
    from ._version import __version__, __version_tuple__
except ImportError:
    __version__ = "unknown"
    __version_tuple__ = (0, 0, 0)  # type: ignore[assignment]

__all__ = ["__version__", "__version_tuple__"]
