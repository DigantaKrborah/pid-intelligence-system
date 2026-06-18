"""
database.py — PostgreSQL connection pool
Provides get_db(), a FastAPI dependency that hands a connection
to a route and returns it to the pool when the request finishes.
"""

import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor

from app.core.config import get_settings

# The pool is created once at startup (see main.py) and reused for every request
_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _psycopg2_dsn(url: str) -> str:
    """Strip SQLAlchemy driver prefix so psycopg2 can parse the DSN."""
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg2://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


def init_db_pool() -> None:
    """
    Create the connection pool.
    Called once from main.py on application startup.
    ThreadedConnectionPool is thread-safe and works well with FastAPI.
    """
    global _pool
    settings = get_settings()

    try:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,           # keep at least 1 connection open
            maxconn=10,          # allow up to 10 simultaneous connections
            dsn=_psycopg2_dsn(settings.database_url),
        )
        print("Database connection pool created successfully.")
    except Exception as err:
        print(f"ERROR: Could not connect to database.\n  {err}")
        print("Check DATABASE_URL in your backend/.env file.")
        raise


def close_db_pool() -> None:
    """Close all connections in the pool. Called on application shutdown."""
    global _pool
    if _pool:
        _pool.closeall()
        print("Database connection pool closed.")


def get_db():
    """
    FastAPI dependency — use with Depends(get_db) in route functions.
    Yields a psycopg2 connection with RealDictCursor (rows come back as dicts).
    Automatically returns the connection to the pool when the request ends.

    Example usage in a route:
        from app.core.database import get_db
        from fastapi import Depends

        @router.get("/example")
        def my_route(db = Depends(get_db)):
            with db.cursor() as cur:
                cur.execute("SELECT 1")
    """
    if _pool is None:
        raise RuntimeError("Database pool is not initialised. Check startup logs.")

    conn = _pool.getconn()
    conn.cursor_factory = RealDictCursor   # rows returned as dict instead of tuple
    try:
        yield conn
        conn.commit()                      # auto-commit on success
    except Exception:
        conn.rollback()                    # roll back on any error
        raise
    finally:
        _pool.putconn(conn)                # always return connection to pool
