"""Async MyMdC Client

TODO: I've copy-pasted this code across a few different projects, when/if an async HTTPX
MyMdC client package is created this can be removed and replaced with calls to that."""
import datetime as dt
from typing import Any, AsyncGenerator

import httpx
from pydantic import HttpUrl, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from zulip_write_only_proxy.exceptions import ZwopException


class MyMdCCredentials(BaseSettings):
    """MyMdC Credentials. Read from `MYMDC_{key}` environment variables/`.env` file.

    Get from from <https://in.xfel.eu/metadata/oauth/applications>.
    """

    id: str
    secret: SecretStr
    email: str
    token_url: HttpUrl

    _access_token: str = ""
    _expires_at: dt.datetime = dt.datetime.fromisocalendar(1970, 1, 1)

    model_config = SettingsConfigDict(env_prefix="mymdc_", env_file=[".env"])


class MyMdCAuth(httpx.Auth, MyMdCCredentials):
    async def acquire_token(self):
        """Acquires a new token if none is stored or if the existing token expired,
        otherwise reuses the existing token.

        Token data stored under `_access_token` and `_expires_at`.
        """
        if self._access_token and self._expires_at >= dt.datetime.now():
            return self._access_token

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
            print(
                "Response from MyMdC missing required fields, check webservice `user-id`"
                f"and `user-secret`. Response: {data=}",
            )
            raise ValueError("Invalid response from MyMdC")

        expires_in = dt.timedelta(seconds=data["expires_in"])
        self._access_token = data["access_token"]
        self._expires_at = dt.datetime.now() + expires_in

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

        res = res.json().get("logbook_info", {}).get("logbook_identifier", None)

        if res is None:
            raise NoStreamForProposalError(proposal_no)

        if not isinstance(res, str):
            raise RuntimeError(f"stream name should be string not {type(res)=} {res=}")

        return res


# crappy "dependency injection"/singleton. Other modules should not instantiate their
# own client and should instead import this client instance.
try:
    client = MyMdCClient()
    """Singleton instance of the MyMdC client."""
except ValidationError as e:
    print(e)  # TODO: better logging
    client = None  # type: ignore[assignment]
