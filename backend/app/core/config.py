from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables.

    Instantiating this class reads and validates the environment immediately,
    so it is never created at import time — see get_settings() below.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["dev", "prod", "test"] = "dev"

    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    cors_allowed_origins: Annotated[list[str], NoDecode] = []

    log_level: str = "INFO"

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def split_comma_separated_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Cached Settings accessor.

    Using this instead of a module-level `settings = Settings()` singleton
    means the environment is only read on first use (e.g. inside a FastAPI
    dependency), not at import time — so importing app modules in tests never
    requires a real environment to already be configured.
    """
    return Settings()
