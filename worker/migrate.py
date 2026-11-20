"""Apply SQL migrations from ./migrations to DATABASE_URL.

    python -m worker.migrate

Safe to run on every deploy: applied versions are recorded in schema_migrations,
concurrent runs are serialised with an advisory lock, and `*_down.sql` files are
never applied. Each migration runs in its own transaction, so a failure leaves
the database at the last good version.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
LOCK_ID = 7_215_901  # arbitrary constant shared by every runner
_UP = re.compile(r"^(\d+)_(?!down\.sql$)[\w-]+\.sql$")

# Databases migrated by hand before this runner existed have the schema but no
# schema_migrations rows. These probes let such a database be baselined instead
# of failing on "relation already exists". New migrations do not need an entry.
_ALREADY_APPLIED = {
    "001_init": "SELECT to_regclass('public.change_records') IS NOT NULL",
    "002_scan_analysis": (
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'scan_results' AND column_name = 'commit_sha')"
    ),
}


def list_migrations(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    """Up-migrations in version order. Down migrations are excluded."""
    return sorted((p for p in directory.iterdir() if _UP.match(p.name)), key=lambda p: p.name)


def connect(url: str, *, wait: float = 90.0, interval: float = 3.0) -> psycopg.Connection:
    """Connect, retrying while a freshly created database is still starting."""
    deadline = time.monotonic() + wait
    while True:
        try:
            return psycopg.connect(url, autocommit=True)
        except psycopg.OperationalError as e:
            if time.monotonic() >= deadline:
                raise
            print(f"database not ready ({str(e).strip().splitlines()[0]}); retrying", flush=True)
            time.sleep(interval)


def migrate(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations. Returns the versions applied (baselined ones excluded)."""
    applied_now: list[str] = []
    conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
        )
        done = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        for path in list_migrations(directory):
            version = path.stem
            if version in done:
                continue
            probe = _ALREADY_APPLIED.get(version)
            if probe and conn.execute(probe).fetchone()[0]:  # type: ignore[index]
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
                print(f"baselined {version} (schema already present)", flush=True)
                continue
            with conn.transaction():
                conn.execute(path.read_text())  # type: ignore[arg-type]
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            applied_now.append(version)
            print(f"applied {version}", flush=True)
    finally:
        conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
    return applied_now


def main() -> int:
    import os

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    with connect(url) as conn:
        applied = migrate(conn)
    print(f"{len(applied)} migration(s) applied" if applied else "schema up to date", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
