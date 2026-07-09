import pytest

from app.core.config import Settings, get_settings


def test_get_settings_reads_env_and_is_cached() -> None:
    settings = get_settings()

    assert settings.environment == "test"
    assert settings.jwt_algorithm == "HS256"
    assert get_settings() is settings  # lru_cache returns the same instance


def test_cors_allowed_origins_splits_comma_separated_string() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        jwt_secret_key="secret",
        cors_allowed_origins="http://a.example, http://b.example",
    )

    assert settings.cors_allowed_origins == ["http://a.example", "http://b.example"]


def test_cors_allowed_origins_defaults_to_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        jwt_secret_key="secret",
    )

    assert settings.cors_allowed_origins == []
