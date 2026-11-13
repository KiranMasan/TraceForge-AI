
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def apply_migrations(db_path: str | Path) -> list[str]:
    db_path = Path(db_path)

    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found: {db_path}")

    migration_files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
    applied: list[str] = []

    connection = sqlite3.connect(str(db_path))
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()

        for migration_file in migration_files:
            name = migration_file.name

            exists = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE migration_name = ?",
                (name,),
            ).fetchone()

            if exists:
                continue

            sql = migration_file.read_text(encoding="utf-8")

            try:
                connection.executescript(
                    "BEGIN IMMEDIATE;\n"
                    + sql
                    + "\nINSERT INTO schema_migrations (migration_name) "
                    + f"VALUES ('{name}');\n"
                    + "COMMIT;"
                )
            except Exception:
                if connection.in_transaction:
                    connection.rollback()
                raise

            applied.append(name)

    finally:
        connection.close()

    return applied


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply pending TraceForge SQLite migrations."
    )
    parser.add_argument(
        "--db",
        required=True,
        help="Path to the SQLite database.",
    )
    args = parser.parse_args()

    applied = apply_migrations(args.db)

    if applied:
        print("Applied migrations:")
        for name in applied:
            print(f"  - {name}")
    else:
        print("Database is already up to date.")


if __name__ == "__main__":
    main()
