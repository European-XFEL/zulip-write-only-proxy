from pathlib import Path

from pydantic import AnyUrl, DirectoryPath, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Auth(BaseSettings):
    client_id: str
    client_secret: SecretStr
    server_metadata_url: AnyUrl = AnyUrl(
        "https://auth.exfldadev01.desy.de/application/o/zwop/.well-known/openid-configuration",
    )


class Settings(BaseSettings):
    debug: bool = True
    address: AnyUrl = AnyUrl("http://127.0.0.1:8000")
    log_level: str = "debug"
    proxy_root_path: str = ""
    session_secret: SecretStr
    config_dir: DirectoryPath = Path(__file__).parent.parent.parent / "config"

    auth: Auth

    model_config = SettingsConfigDict(
        env_prefix="ZWOP_", env_file=[".env"], env_nested_delimiter="__"
    )


settings = Settings()  # type: ignore
