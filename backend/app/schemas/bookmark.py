import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookmarkCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    tags: list[str] = Field(default_factory=list)


class BookmarkUpdate(BaseModel):
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    tags: list[str] | None = None


class BookmarkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    title: str
    description: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def _tag_names(cls, value: object) -> object:
        """Accepts either plain strings or the ORM Tag objects loaded on
        Bookmark.tags, so the same schema works whether it's built from a
        fresh service-layer object or (in tests) a hand-built dict.
        """
        if isinstance(value, list):
            return [item.name if hasattr(item, "name") else item for item in value]
        return value


class BookmarkPage(BaseModel):
    items: list[BookmarkRead]
    total: int
    limit: int
    offset: int
