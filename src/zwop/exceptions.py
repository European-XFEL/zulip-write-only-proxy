from fastapi import HTTPException


class ZwopException(HTTPException):
    """Base exception class for application. Should be subclasses with a more
    descriptive name.

    It is a `HTTPException` since the primary entrypoint is the HTTP API.
    """
