import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.bookmark import BookmarkCreate, BookmarkPage, BookmarkRead, BookmarkUpdate
from app.services import bookmark_service

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.post("", response_model=BookmarkRead, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    payload: BookmarkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookmarkRead:
    bookmark = await bookmark_service.create_bookmark(
        db,
        user=current_user,
        url=payload.url,
        title=payload.title,
        description=payload.description,
        tag_names=payload.tags,
    )
    await db.commit()
    return BookmarkRead.model_validate(bookmark)


@router.get("", response_model=BookmarkPage)
async def list_bookmarks(
    tag: str | None = None,
    q: str | None = Query(default=None, description="Search title, url, and description"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookmarkPage:
    page = await bookmark_service.list_bookmarks(
        db, user=current_user, tag=tag, search=q, limit=limit, offset=offset
    )
    return BookmarkPage(
        items=[BookmarkRead.model_validate(b) for b in page.items],
        total=page.total,
        limit=limit,
        offset=offset,
    )


@router.get("/{bookmark_id}", response_model=BookmarkRead)
async def get_bookmark(
    bookmark_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookmarkRead:
    try:
        bookmark = await bookmark_service.get_bookmark(
            db, user=current_user, bookmark_id=bookmark_id
        )
    except bookmark_service.BookmarkNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bookmark not found") from exc
    return BookmarkRead.model_validate(bookmark)


@router.patch("/{bookmark_id}", response_model=BookmarkRead)
async def update_bookmark(
    bookmark_id: uuid.UUID,
    payload: BookmarkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookmarkRead:
    data = payload.model_dump(exclude_unset=True)
    tag_names = data.pop("tags", None)
    try:
        bookmark = await bookmark_service.update_bookmark(
            db, user=current_user, bookmark_id=bookmark_id, fields=data, tag_names=tag_names
        )
    except bookmark_service.BookmarkNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bookmark not found") from exc
    await db.commit()
    return BookmarkRead.model_validate(bookmark)


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await bookmark_service.delete_bookmark(db, user=current_user, bookmark_id=bookmark_id)
    except bookmark_service.BookmarkNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bookmark not found") from exc
    await db.commit()
