"""Runtime configuration, read from the environment or a local .env file.

No credential is ever hardcoded here. The Phase 1 database is authoritative,
so DB_NAME defaults to it but may still be overridden for a test schema.
"""

from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "smart_campus_placement"
    db_user: str = "campus_app"
    db_password: str = ""

    # When DB_PASSWORD is empty, let the MySQL client library read the
    # credentials from a local option file, the same way the `mysql` CLI does.
    # The file is never read, printed or committed by this application.
    db_option_file: str = "~/.my.cnf"

    api_title: str = "Smart Campus Placement Management System API"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def database_url(self) -> str:
        auth = quote_plus(self.db_user)
        if self.db_password:
            auth += f":{quote_plus(self.db_password)}"
        return (
            f"mysql+pymysql://{auth}@{self.db_host}:{self.db_port}"
            f"/{self.db_name}?charset=utf8mb4"
        )

    @property
    def connect_args(self) -> dict[str, str]:
        if self.db_password:
            return {}
        path = Path(self.db_option_file).expanduser()
        return {"read_default_file": str(path)} if path.is_file() else {}

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
