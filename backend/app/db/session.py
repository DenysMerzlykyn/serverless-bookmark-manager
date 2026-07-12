from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Cached engine accessor — lazy so importing this module never opens a
    connection or requires DATABASE_URL to be set until it's actually used.
    """
    return create_async_engine(
        get_settings().database_url,
        pool_pre_ping=True,
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
        connect_args={"statement_cache_size": 0},
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped AsyncSession."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        yield session
