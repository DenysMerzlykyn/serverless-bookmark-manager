import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, InvalidHashError

from app.core.config import Settings

_password_hasher = PasswordHasher()

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Returns False (never raises) for a wrong password *or* a malformed/
    corrupted hash — either case should surface to the caller as "invalid
    credentials", not a 500.
    """
    try:
        return _password_hasher.verify(hashed_password, password)
    except (Argon2Error, InvalidHashError):
        # InvalidHashError is a ValueError, not an Argon2Error subclass —
        # both need catching to cover "wrong password" and "malformed hash".
        return False


def create_access_token(*, subject: str, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Raises jwt.PyJWTError (or a subclass) on any invalid/expired/
    wrong-type token — callers map that to a 401, they don't need to
    inspect the payload to find out something's wrong.
    """
    payload: dict[str, Any] = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("token is not an access token")
    return payload


def generate_refresh_token() -> str:
    """Opaque, high-entropy token handed to the client. Only its hash is
    ever stored (see hash_refresh_token) — a DB read of refresh_tokens can't
    be used to impersonate a user.
    """
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
