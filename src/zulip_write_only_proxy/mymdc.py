import datetime as dt
from typing import Any, AsyncGenerator

import httpx
from pydantic import HttpUrl, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        """Adds required authorization headers to the request."""
        bearer_token = await self.acquire_token()

        request.headers["Authorization"] = f"Bearer {bearer_token}"
        request.headers["accept"] = "application/json; version=1"
        request.headers["X-User-Email"] = self.email

        yield request


class MyMdCClient(httpx.AsyncClient):
    def __init__(self, auth: MyMdCAuth | None = None) -> None:
        """Client for the MyMdC API."""
        if auth is None:
            auth = MyMdCAuth()  # type: ignore

        super().__init__(auth=auth)

    async def get_zulip_stream_name(self, proposal_no: int) -> str | None:
        """Get the Zulip stream name for a given proposal number."""
        # TODO: should use `/proposals/{number}/logbook`, but this responds with 403
        res = await self.get(
            f"https://in.xfel.eu/metadata/api/proposals/by_number/{proposal_no}"
        )

        return res.json().get("logbook_info", {}).get("logbook_identifier", None)

