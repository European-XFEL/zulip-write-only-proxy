from pathlib import Path

from pydantic import FilePath
from pydantic_settings import BaseSettings


class Mtls(BaseSettings):
    cert_file: FilePath = Path("./certs/server.crt")
    key_file: FilePath = Path("./certs/server.key")
    ca_file: FilePath = Path("./certs/ca.crt")


class Settings(BaseSettings):
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8443
    mtls: Mtls = Mtls()


settings = Settings()
