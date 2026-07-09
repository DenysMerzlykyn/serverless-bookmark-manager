from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        jwt_secret_key="unit-test-secret-padded-to-32-bytes-min",
    )


def test_hash_password_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")

    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("correct horse battery staple")

    assert verify_password("wrong password", hashed) is False


def test_verify_password_rejects_malformed_hash() -> None:
    assert verify_password("anything", "not-a-real-argon2-hash") is False


def test_access_token_roundtrip(settings: Settings) -> None:
    token = create_access_token(subject="user-123", settings=settings)

    payload = decode_access_token(token, settings)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_decode_access_token_rejects_expired_token(settings: Settings) -> None:
    now = datetime.now(UTC)
    expired_payload = {
        "sub": "user-123",
        "iat": now - timedelta(minutes=30),
        "exp": now - timedelta(minutes=15),
        "type": "access",
    }
    expired_token = jwt.encode(
        expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token, settings)


def test_decode_access_token_rejects_non_access_token_type(settings: Settings) -> None:
    now = datetime.now(UTC)
    refresh_shaped_payload = {
        "sub": "user-123",
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "type": "refresh",
    }
    token = jwt.encode(
        refresh_shaped_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, settings)


def test_decode_access_token_rejects_wrong_secret(settings: Settings) -> None:
    token = create_access_token(subject="user-123", settings=settings)
    wrong_secret_settings = settings.model_copy(
        update={"jwt_secret_key": "a-different-secret-also-padded-32-bytes"}
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token, wrong_secret_settings)


def test_generate_refresh_token_is_random_and_high_entropy() -> None:
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first != second
    assert len(first) > 32


def test_hash_refresh_token_is_deterministic_and_one_way() -> None:
    token = generate_refresh_token()

    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token
