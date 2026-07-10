import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Bookmark, Tag, User


class BookmarkNotFoundError(Exception):
    pass


async def _get_or_create_tags(session: AsyncSession, *, user: User, names: list[str]) -> list[Tag]:
    normalized = {name.strip() for name in names if name.strip()}
    if not normalized:
        return []

    existing = await session.scalars(
        select(Tag).where(Tag.user_id == user.id, Tag.name.in_(list(normalized)))
    )
    tags_by_name = {tag.name: tag for tag in existing}

    for name in normalized:
        if name not in tags_by_name:
            tag = Tag(user_id=user.id, name=name)
            session.add(tag)
            tags_by_name[name] = tag

    await session.flush()
    return list(tags_by_name.values())


async def create_bookmark(
    session: AsyncSession,
    *,
    user: User,
    url: str,
    title: str,
    description: str | None,
    tag_names: list[str],
) -> Bookmark:
    tags = await _get_or_create_tags(session, user=user, names=tag_names)
    bookmark = Bookmark(user_id=user.id, url=url, title=title, description=description, tags=tags)
    session.add(bookmark)
    await session.flush()
    return bookmark


async def get_bookmark(session: AsyncSession, *, user: User, bookmark_id: uuid.UUID) -> Bookmark:
    bookmark = await session.scalar(
        select(Bookmark)
        .where(Bookmark.id == bookmark_id, Bookmark.user_id == user.id)
        .options(selectinload(Bookmark.tags))
    )
    if bookmark is None:
        # Not found and "belongs to someone else" both raise this - a 404
        # either way avoids confirming a given bookmark ID exists at all.
        raise BookmarkNotFoundError
    return bookmark


@dataclass
class BookmarkPage:
    items: list[Bookmark]
    total: int


async def list_bookmarks(
    session: AsyncSession,
    *,
    user: User,
    tag: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> BookmarkPage:
    filters = [Bookmark.user_id == user.id]
    if tag:
        filters.append(Bookmark.tags.any(Tag.name == tag))
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Bookmark.title.ilike(pattern),
                Bookmark.url.ilike(pattern),
                Bookmark.description.ilike(pattern),
            )
        )

    total = await session.scalar(select(func.count()).select_from(Bookmark).where(*filters))

    items = await session.scalars(
        select(Bookmark)
        .where(*filters)
        .options(selectinload(Bookmark.tags))
        .order_by(Bookmark.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return BookmarkPage(items=list(items), total=total or 0)


async def update_bookmark(
    session: AsyncSession,
    *,
    user: User,
    bookmark_id: uuid.UUID,
    fields: dict[str, Any],
    tag_names: list[str] | None,
) -> Bookmark:
    bookmark = await get_bookmark(session, user=user, bookmark_id=bookmark_id)
    for key, value in fields.items():
        setattr(bookmark, key, value)
    if tag_names is not None:
        bookmark.tags = await _get_or_create_tags(session, user=user, names=tag_names)
    await session.flush()
    return bookmark


async def delete_bookmark(session: AsyncSession, *, user: User, bookmark_id: uuid.UUID) -> None:
    bookmark = await get_bookmark(session, user=user, bookmark_id=bookmark_id)
    await session.delete(bookmark)
    await session.flush()
