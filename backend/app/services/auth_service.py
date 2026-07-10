import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models import RefreshToken, User


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class RefreshTokenReuseDetectedError(InvalidRefreshTokenError):
    pass


async def register_user(session: AsyncSession, *, email: str, password: str) -> User:
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(email=email, hashed_password=hash_password(password))
    session.add(user)
    await session.flush()
    return user


async def authenticate_user(session: AsyncSession, *, email: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.hashed_password):
        # Deliberately the same error for "no such user" and "wrong password"
        # — distinguishing them lets an attacker enumerate valid emails.
        raise InvalidCredentialsError
    return user


async def _issue_token_pair(
    session: AsyncSession, *, user: User, settings: Settings, family_id: uuid.UUID
) -> tuple[str, str]:
    access_token = create_access_token(subject=str(user.id), settings=settings)

    refresh_token = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await session.flush()
    return access_token, refresh_token


async def login(
    session: AsyncSession, *, email: str, password: str, settings: Settings
) -> tuple[str, str]:
    user = await authenticate_user(session, email=email, password=password)
    return await _issue_token_pair(session, user=user, settings=settings, family_id=uuid.uuid4())


async def refresh_tokens(
    session: AsyncSession, *, presented_token: str, settings: Settings
) -> tuple[str, str]:
    """Rotates a refresh token: the presented token is revoked and a new one
    issued in its place, sharing the same family_id.

    If the presented token was already revoked (i.e. it was already used
    once, or logged out), that's a replay — the entire family is burned so a
    stolen-then-rotated token can't keep producing valid access tokens.
    """
    token_hash = hash_refresh_token(presented_token)
    stored = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    if stored is None:
        raise InvalidRefreshTokenError

    if stored.revoked_at is not None:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == stored.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await session.flush()
        raise RefreshTokenReuseDetectedError

    if stored.expires_at < datetime.now(UTC):
        raise InvalidRefreshTokenError

    user = await session.get(User, stored.user_id)
    assert user is not None  # FK guarantees a matching user row exists

    access_token, new_refresh_token = await _issue_token_pair(
        session, user=user, settings=settings, family_id=stored.family_id
    )

    new_stored = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(new_refresh_token))
    )
    assert new_stored is not None
    stored.revoked_at = datetime.now(UTC)
    stored.replaced_by_id = new_stored.id
    await session.flush()

    return access_token, new_refresh_token


async def logout(session: AsyncSession, *, presented_token: str) -> None:
    token_hash = hash_refresh_token(presented_token)
    stored = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        await session.flush()
