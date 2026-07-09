import asyncio
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.db.session import get_engine, get_sessionmaker


def _run_migrations_to_head() -> None:
    """Applies the real Alembic migrations to the test database, so
    integration tests validate the migration files themselves — not just
    whatever the current models happen to say.

    alembic/env.py calls asyncio.run() internally, which cannot be nested
    inside the event loop pytest-asyncio is already running this fixture in
    — hence running it in a separate thread via asyncio.to_thread, where
    asyncio.run() is free to create its own loop.
    """
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(alembic_cfg, "head")


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def _migrated_schema() -> None:
    await asyncio.to_thread(_run_migrations_to_head)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Yields a session bound to a connection-level transaction that is
    always rolled back afterwards, so tests never leave data behind or see
    each other's writes — regardless of whether the code under test calls
    session.commit() (join_transaction_mode="create_savepoint" converts an
    inner commit into a SAVEPOINT release instead of ending the outer
    transaction).

    get_engine()/get_sessionmaker() are process-wide caches in app code —
    correct for a long-lived Lambda process, but pytest-asyncio gives each
    test function its own event loop, and asyncpg connections can't be
    reused across loops. So each test clears the cache and builds (then
    disposes) its own engine, rather than sharing the one from app code.
    """
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    engine = get_engine()
    connection = await engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()
