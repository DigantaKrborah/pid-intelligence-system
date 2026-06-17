"""
create_db.py — Database setup utility
Run this once to create the PostgreSQL database and apply the schema.
Usage (from the /backend folder): python app/utils/create_db.py
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# ── Load .env ──────────────────────────────────────────────────────────────────
# .env lives one level up from app/utils/ → in backend/
from dotenv import load_dotenv

ENV_FILE = Path(__file__).parent.parent.parent / ".env"
if not ENV_FILE.exists():
    print(f"ERROR: .env file not found at {ENV_FILE}")
    print("Copy backend/.env.example to backend/.env and fill in your values.")
    sys.exit(1)

load_dotenv(dotenv_path=ENV_FILE)

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL is not set in your .env file.")
    sys.exit(1)

# ── Parse connection details from DATABASE_URL ─────────────────────────────────
# Expected format: postgresql://username:password@host:port/dbname
parsed = urlparse(DATABASE_URL)

DB_USER     = parsed.username          # e.g. postgres
DB_PASSWORD = parsed.password          # your postgres password
DB_HOST     = parsed.hostname          # e.g. localhost
DB_PORT     = parsed.port or 5432      # default PostgreSQL port
DB_NAME     = parsed.path.lstrip("/")  # e.g. pid_system

# ── Path to schema.sql ────────────────────────────────────────────────────────
# schema.sql is at /db/schema.sql — two levels above /backend/
SCHEMA_FILE = Path(__file__).parent.parent.parent.parent / "db" / "schema.sql"

if not SCHEMA_FILE.exists():
    print(f"ERROR: schema.sql not found at {SCHEMA_FILE}")
    sys.exit(1)

# ── Step 1: Create the database if it does not exist ──────────────────────────
def create_database():
    """
    Connect to the default 'postgres' system database first,
    then create our application database if it does not already exist.
    We must use autocommit=True for CREATE DATABASE to work in PostgreSQL.
    """
    import psycopg2
    from psycopg2 import sql

    print(f"Connecting to PostgreSQL at {DB_HOST}:{DB_PORT} as '{DB_USER}'...")

    # Connect to the built-in 'postgres' database (always exists)
    conn = psycopg2.connect(
        dbname="postgres",
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.autocommit = True  # Required for CREATE DATABASE

    cursor = conn.cursor()

    # Check if our database already exists
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (DB_NAME,)
    )
    exists = cursor.fetchone()

    if exists:
        print(f"Database '{DB_NAME}' already exists — skipping creation.")
    else:
        cursor.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME))
        )
        print(f"Database '{DB_NAME}' created successfully.")

    cursor.close()
    conn.close()


# ── Step 2: Apply the schema ──────────────────────────────────────────────────
def apply_schema():
    """
    Connect to our application database and run schema.sql.
    This creates all 13 tables. If a table already exists, it is skipped
    because the schema uses CREATE TABLE IF NOT EXISTS (or equivalent).
    """
    import psycopg2

    print(f"\nConnecting to database '{DB_NAME}'...")
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.autocommit = False
    cursor = conn.cursor()

    print(f"Reading schema from: {SCHEMA_FILE}")
    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")

    try:
        cursor.execute(schema_sql)
        conn.commit()
        print("\nSchema applied successfully. Tables created:")

        # List all tables that now exist in the database
        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        )
        tables = cursor.fetchall()
        for (table_name,) in tables:
            print(f"  ✓  {table_name}")

    except Exception as err:
        conn.rollback()
        print(f"\nERROR applying schema: {err}")
        raise

    finally:
        cursor.close()
        conn.close()


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  P&ID Intelligence System — Database Setup")
    print("=" * 55)
    try:
        create_database()
        apply_schema()
        print("\nSetup complete! Database is ready.")
    except Exception as e:
        print(f"\nSetup failed: {e}")
        sys.exit(1)
