import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bookmark, Tag, User


def _make_user(suffix: str = "") -> User:
    return User(email=f"user{suffix}-{uuid.uuid4()}@example.com", hashed_password="not-a-real-hash")


async def test_create_user_and_query_back(db_session: AsyncSession) -> None:
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    fetched = await db_session.get(User, user.id)

    assert fetched is not None
    assert fetched.email == user.email


async def test_user_email_unique_constraint(db_session: AsyncSession) -> None:
    email = f"dup-{uuid.uuid4()}@example.com"
    db_session.add(User(email=email, hashed_password="hash-one"))
    await db_session.flush()

    db_session.add(User(email=email, hashed_password="hash-two"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_bookmark_cascade_deletes_at_database_level_on_user_delete(
    db_session: AsyncSession,
) -> None:
    user = _make_user("-cascade")
    db_session.add(user)
    await db_session.flush()

    bookmark = Bookmark(user_id=user.id, url="https://example.com", title="Example")
    db_session.add(bookmark)
    await db_session.flush()
    bookmark_id = bookmark.id

    # Delete via a raw Core statement (not session.delete(user)) to prove the
    # ON DELETE CASCADE foreign key in the migration itself does the work,
    # independent of the ORM-level cascade="all, delete-orphan" setting.
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.flush()

    # populate_existing=True forces a real SELECT instead of returning the
    # (now stale) copy still sitting in the session's identity map — without
    # it this assertion would pass for the wrong reason even if the FK
    # ondelete=CASCADE were broken.
    remaining = await db_session.get(Bookmark, bookmark_id, populate_existing=True)
    assert remaining is None


async def test_tag_name_is_unique_per_user_but_not_across_users(db_session: AsyncSession) -> None:
    user_a = _make_user("-a")
    user_b = _make_user("-b")
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    db_session.add(Tag(user_id=user_a.id, name="reading"))
    await db_session.flush()

    # begin_nested() opens an explicit SAVEPOINT: when the block raises, only
    # that savepoint rolls back, leaving db_session usable for the rest of
    # the test — unlike a plain flush() failure, which would poison the
    # whole transaction.
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(Tag(user_id=user_a.id, name="reading"))
            await db_session.flush()

    # Same tag name for a *different* user is allowed.
    db_session.add(Tag(user_id=user_b.id, name="reading"))
    await db_session.flush()  # should not raise


async def test_bookmark_tag_many_to_many_relationship(db_session: AsyncSession) -> None:
    user = _make_user("-m2m")
    db_session.add(user)
    await db_session.flush()

    tag = Tag(user_id=user.id, name="devops")
    bookmark = Bookmark(user_id=user.id, url="https://example.com", title="Example")
    bookmark.tags.append(tag)
    db_session.add(bookmark)
    await db_session.flush()

    reloaded_bookmark = (
        await db_session.execute(select(Bookmark).where(Bookmark.id == bookmark.id))
    ).scalar_one()
    tag_names = {t.name for t in await reloaded_bookmark.awaitable_attrs.tags}

    assert tag_names == {"devops"}
