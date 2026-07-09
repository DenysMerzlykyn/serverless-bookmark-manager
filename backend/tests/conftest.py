"""Sets default env vars for every test *before* any `app.*` module is
imported, since Settings() validates required fields (DATABASE_URL,
JWT_SECRET_KEY) at instantiation time. pytest always collects conftest.py
before the test modules in the same directory, so this ordering is reliable.

Using setdefault() means a real .env or exported env var still wins locally,
but CI (which has neither) gets safe, working test values automatically.
"""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://bookmarks:bookmarks@localhost:5432/bookmarks_test"
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production-use")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
