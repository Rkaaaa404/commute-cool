"""Database connection pool for Teduh API.

Uses asyncpg for async queries directly (lightweight, no ORM overhead).
"""

import os
from contextlib import asynccontextmanager

import asyncpg

DATABASE_URL = os.getenv(
    "ASYNC_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://cc_user:cc_dev_pass@localhost:5432/commute_cool")
)

# Convert SQLAlchemy-style URL to asyncpg format
_asyncpg_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Pool tuning (env-overridable). On AWS Lambda + Supabase transaction pooler use:
#   DB_POOL_MIN=0, DB_POOL_MAX=3, DB_STATEMENT_CACHE_SIZE=0
DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "2"))
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))
DB_STATEMENT_CACHE_SIZE = int(os.getenv("DB_STATEMENT_CACHE_SIZE", "100"))

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            _asyncpg_url,
            min_size=DB_POOL_MIN,
            max_size=DB_POOL_MAX,
            command_timeout=30,
            statement_cache_size=DB_STATEMENT_CACHE_SIZE,
            max_inactive_connection_lifetime=60,
        )
    return _pool


async def close_pool():
    """Close connection pool on shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_conn():
    """Get a connection from the pool."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn
