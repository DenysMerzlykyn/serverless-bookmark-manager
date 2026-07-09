from app.db.session import get_db

__all__ = ["get_db"]

# get_current_user (JWT verification) is added in the auth stage, once
# app/core/security.py exists — deliberately not stubbed out here.
