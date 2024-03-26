import datetime as dt
from pathlib import Path

from pydantic import AnyUrl, DirectoryPath, FilePath, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    _expires_at: dt.datetime = dt.datetime.fromisocalendar(1970, 1, 1).astimezone(
        dt.timezone.utc
    )


class TokenWriter(BaseSettings):
    ssh_destination: str = "xdana@max-exfl.desy.de"
    ssh_private_key: FilePath = (
        Path(__file__).parent.parent.parent / "config/id_ed25519"
    )
    ssh_known_hosts: FilePath = (
        Path(__file__).parent.parent.parent / "config/known_hosts"
    )
    zwop_url: HttpUrl = AnyUrl("https://exfldadev01.desy.de/zwop")


class Settings(BaseSettings):
    debug: bool = True
    address: AnyUrl = AnyUrl("http://127.0.0.1:8000")
    log_level: str = "debug"
    proxy_root: str = ""
    session_secret: SecretStr
    config_dir: DirectoryPath = Path(__file__).parent.parent.parent / "config"

    auth: Auth
    mymdc: MyMdCCredentials
    token_writer: TokenWriter = TokenWriter()

    model_config = SettingsConfigDict(
        env_prefix="ZWOP_", env_file=[".env"], env_nested_delimiter="__"
    )


settings = Settings()  # type: ignore[call-arg]
