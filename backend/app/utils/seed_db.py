"""
seed_db.py — Seed data utility
Inserts the initial organization, admin user, and process units.
Safe to run multiple times — skips rows that already exist.
Usage (from the /backend folder): python app/utils/seed_db.py
"""

import os
import sys
from pathlib import Path

# ── Load .env ──────────────────────────────────────────────────────────────────
# .env lives at backend/.env — three levels up from backend/app/utils/
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

# ── Path to seed.sql ──────────────────────────────────────────────────────────
# seed.sql is at /db/seed.sql — four levels up from backend/app/utils/
SEED_FILE = Path(__file__).parent.parent.parent.parent / "db" / "seed.sql"

if not SEED_FILE.exists():
    print(f"ERROR: seed.sql not found at {SEED_FILE}")
    sys.exit(1)

# ── Parse DATABASE_URL ────────────────────────────────────────────────────────
from urllib.parse import urlparse

parsed     = urlparse(DATABASE_URL)
DB_USER    = parsed.username
DB_PASSWORD = parsed.password
DB_HOST    = parsed.hostname
DB_PORT    = parsed.port or 5432
DB_NAME    = parsed.path.lstrip("/")


# ── Run seed.sql against the database ────────────────────────────────────────
def run_seed():
    """
    Read seed.sql and execute it against the pid_system database.
    ON CONFLICT DO NOTHING in the SQL means no error if rows already exist.
    """
    import psycopg2

    print("=" * 55)
    print("  P&ID Intelligence System — Seed Data")
    print("=" * 55)
    print(f"Connecting to database '{DB_NAME}' at {DB_HOST}:{DB_PORT}...")

    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.autocommit = False
    cursor = conn.cursor()

    print(f"Reading seed data from: {SEED_FILE}\n")
    seed_sql = SEED_FILE.read_text(encoding="utf-8")

    try:
        cursor.execute(seed_sql)
        conn.commit()

        # Show how many rows exist in each seeded table
        for table in ("organizations", "users", "process_units"):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  ✓  {table}: {count} row(s)")

        print("\nSeed data inserted successfully.")

    except Exception as err:
        conn.rollback()
        print(f"\nERROR running seed: {err}")
        raise

    finally:
        cursor.close()
        conn.close()


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        run_seed()
    except Exception as e:
        print(f"\nSeed failed: {e}")
        sys.exit(1)
