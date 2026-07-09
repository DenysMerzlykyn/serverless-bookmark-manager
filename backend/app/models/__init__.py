"""Import every model module here so Base.metadata is fully populated for
Alembic autogenerate — a model that's never imported is invisible to it.
"""

from app.models.bookmark import Bookmark
from app.models.refresh_token import RefreshToken
from app.models.tag import Tag
from app.models.user import User

__all__ = ["Bookmark", "RefreshToken", "Tag", "User"]
