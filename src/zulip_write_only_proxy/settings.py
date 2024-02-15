import datetime as dt
from pathlib import Path

from pydantic import AnyUrl, DirectoryPath, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .repositories import ClientRepository, ZuliprcRepository


class Auth(BaseSettings):
    client_id: str
    client_secret: SecretStr
    server_metadata_url: AnyUrl = AnyUrl(
        "https://auth.exfldadev01.desy.de/application/o/zwop/.well-known/openid-configuration",
    )


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


class Settings(BaseSettings):
    debug: bool = True
    address: AnyUrl = AnyUrl("http://127.0.0.1:8000")
    log_level: str = "debug"
    proxy_root_path: str = ""
    session_secret: SecretStr
    config_dir: DirectoryPath = Path(__file__).parent.parent.parent / "config"

    auth: Auth
    mymdc: MyMdCCredentials
    clients: ClientRepository
    zuliprcs: ZuliprcRepository

    model_config = SettingsConfigDict(
        env_prefix="ZWOP_", env_file=[".env"], env_nested_delimiter="__"
    )


settings = Settings()  # type: ignore[call-arg]