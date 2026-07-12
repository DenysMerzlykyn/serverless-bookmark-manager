from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Any

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def build_engine_args(database_url: str) -> tuple[URL, dict[str, Any]]:
    """Shared by app/db/session.py and alembic/env.py, which each create
    their own engine - this is the one place the URL/connect_args logic
    below is written.

    SQLAlchemy's asyncpg dialect forwards any query param it doesn't
    recognize straight through as a connect() keyword argument - but
    Neon's connection strings include "sslmode"/"channel_binding" by
    default, which are libpq DSN-string names asyncpg's keyword API
    doesn't accept (it wants "ssl", not "sslmode"). Passing them through
    as-is fails with "connect() got an unexpected keyword argument
    'sslmode'". Strip them and request TLS explicitly instead, only when
    the URL actually asked for it - a plain local Postgres URL (no
    sslmode) is left untouched.
    """
    url = make_url(database_url)
    query = dict(url.query)
    wants_ssl = query.pop("sslmode", None) not in (None, "disable")
    query.pop("channel_binding", None)
    url = url.set(query=query)

    connect_args: dict[str, Any] = {
        # Neon's pooled connection endpoint (PgBouncer, transaction mode) is
        # the right choice for Lambda specifically - many concurrent
        # execution environments could otherwise exhaust Postgres's
        # connection limit fast. But transaction-mode pooling can hand the
        # same underlying connection to different logical sessions between
        # queries, and asyncpg's default server-side prepared-statement
        # cache assumes one connection is a stable session - that mismatch
        # surfaces as "prepared statement does not exist" errors. Disabling
        # the cache costs a small amount of performance (statements are
        # re-parsed each time) but is required for correctness through the
        # pooler; harmless against a direct (unpooled) connection too.
        "statement_cache_size": 0
    }
    if wants_ssl:
        connect_args["ssl"] = True

    return url, connect_args


@lru_cache
def get_engine() -> AsyncEngine:
    """Cached engine accessor — lazy so importing this module never opens a
    connection or requires DATABASE_URL to be set until it's actually used.
    """
    url, connect_args = build_engine_args(get_settings().database_url)
    return create_async_engine(url, pool_pre_ping=True, connect_args=connect_args)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped AsyncSession."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        yield session
