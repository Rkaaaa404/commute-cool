"""Database connection pool for COMMUTE-COOL API.

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

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            _asyncpg_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
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
