"""Async MyMdC Client

TODO: I've copy-pasted this code across a few different projects, when/if an async HTTPX
MyMdC client package is created this can be removed and replaced with calls to that."""

import datetime as dt
from typing import TYPE_CHECKING, Any, AsyncGenerator

import httpx

from . import logger
from .exceptions import ZwopException
from .settings import MyMdCCredentials, Settings

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI


CLIENT: "MyMdCClient" = None  # type: ignore[assignment]


def configure(settings: Settings, _: "FastAPI"):
    global CLIENT
    logger.info("Configuring MyMdC client", settings=settings.mymdc)
    auth = MyMdCAuth.model_validate(settings.mymdc, from_attributes=True)
    CLIENT = MyMdCClient(auth=auth)


class MyMdCAuth(httpx.Auth, MyMdCCredentials):
    async def acquire_token(self):
        """Acquires a new token if none is stored or if the existing token expired,
        otherwise reuses the existing token.

        Token data stored under `_access_token` and `_expires_at`.
        """
        expired = self._expires_at <= dt.datetime.now(tz=dt.timezone.utc)
        if self._access_token and not expired:
            logger.debug("Reusing existing MyMdC token", expires_at=self._expires_at)
            return self._access_token

        logger.info(
            "Requesting new MyMdC token",
            access_token_none=not self._access_token,
            expires_at=self._expires_at,
            expired=expired,
        )

        async with httpx.AsyncClient() as client:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.id,
                "client_secret": self.secret.get_secret_value(),
                "scope": "public",
            }

            response = await client.post(str(self.token_url), data=data)

        data = response.json()

        if any(k not in data for k in ["access_token", "expires_in"]):
            logger.critical(
                "Response from MyMdC missing required fields, check webservice "
                "`user-id` and `user-secret`.",
                response=response.text,
                status_code=response.status_code,
            )
            msg = "Invalid response from MyMdC"
            raise ValueError(msg)  # TODO: custom exception, frontend feedback

        expires_in = dt.timedelta(seconds=data["expires_in"])
        self._access_token = data["access_token"]
        self._expires_at = dt.datetime.now(tz=dt.timezone.utc) + expires_in

        logger.info("Acquired new MyMdC token", expires_at=self._expires_at)
        return self._access_token

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, Any]:
        """Fetches bearer token (if required) and adds required authorization headers to
        the request.

        Yields:
            AsyncGenerator[httpx.Request, Any]: yields `request` with additional headers
        """
        bearer_token = await self.acquire_token()

        request.headers["Authorization"] = f"Bearer {bearer_token}"
        request.headers["accept"] = "application/json; version=1"
        request.headers["X-User-Email"] = self.email

        yield request


class MyMdCResponseError(ZwopException):
    def __init__(self, res: httpx.Response):
        super().__init__(status_code=res.status_code, detail=res.json())


class NoStreamForProposalError(ZwopException):
    """Raised when no stream name is found for a given proposal number, can occur if the
    proposal does not have a Zulip eLog configured, or if the proposal does not exist.
    """

    def __init__(self, proposal_no: int):
        super().__init__(
            status_code=404, detail=f"No stream name found for proposal {proposal_no}"
        )


class MyMdCClient(httpx.AsyncClient):
    def __init__(self, auth: MyMdCAuth | None = None) -> None:
        """Client for the MyMdC API."""
        if auth is None:
            auth = MyMdCAuth()  # type: ignore[call-arg]

        super().__init__(auth=auth, base_url="https://in.xfel.eu/metadata/")

    async def get_zulip_stream_name(self, proposal_no: int) -> str:
        """Get the Zulip stream name for a given proposal number.

        Raises:
            NoStreamForProposalError: if no stream name is found for the proposal, or if
            the proposal is non-existent.

        Returns:
            str: The stream name.
        """
        # TODO: should use `/proposals/{number}/logbook`, but this responds with 403
        res = await self.get(f"/api/proposals/by_number/{proposal_no}")

        res_dict = res.json()

        stream_name = res_dict.get("logbook_info", {}).get("logbook_identifier", None)

        if res.status_code == 404 or res_dict is None:
            raise MyMdCResponseError(res)

        if stream_name is None:
            raise NoStreamForProposalError(proposal_no)

        if not isinstance(stream_name, str):
            msg = f"stream name should be string not {type(res)=} {res=}"
            raise RuntimeError(msg)

        return stream_name

    async def get_zulip_bot_credentials(self, proposal_no: int) -> dict:
        res = await self.get(f"/api/proposals/{proposal_no}/logbook_bot")

        res_dict = res.json()

        if res.status_code == 404 or res_dict is None:
            raise MyMdCResponseError(res)

        return res_dict

    async def get_proposal_id(self, proposal_no: int) -> int:
        res = await self.get(f"/api/proposals/by_number/{proposal_no}")

        res_dict = res.json()

        if res.status_code == 404 or res_dict is None:
            raise MyMdCResponseError(res)

        proposal_id = res_dict.get("id")

        if proposal_id is None:
            msg = "MyMdC response for did not contain `id`"
            raise RuntimeError(msg)

        return proposal_id
