"""One-time database setup: creates the "campusfix" database, its tables and sample data.

Run it from the backend folder (with the virtual environment active):
    python setup_database.py

It reads the connection details from backend/.env, so psql is NOT needed.

WARNING: it runs database/schema.sql, which DELETES all existing CampusFix data
and creates empty tables, then database/seed.sql adds the sample users and complaints.
"""

from pathlib import Path

import psycopg
from psycopg import sql

from app.config import settings

DATABASE_FOLDER = Path(__file__).resolve().parent.parent / "database"
SCHEMA_FILE = DATABASE_FOLDER / "schema.sql"
SEED_FILE = DATABASE_FOLDER / "seed.sql"


def connect_to(database_name: str, autocommit: bool = False) -> psycopg.Connection:
    """Open a connection to the given database using the settings from .env."""
    return psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=database_name,
        user=settings.db_user,
        password=settings.db_password,
        autocommit=autocommit,
    )


def create_database_if_missing() -> None:
    """Create the CampusFix database if it does not exist yet.

    CREATE DATABASE cannot run inside a transaction, so we connect to the
    built-in "postgres" database with autocommit switched on.
    """
    with connect_to("postgres", autocommit=True) as connection:
        already_exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (settings.db_name,)
        ).fetchone()
        if already_exists:
            print(f"Database '{settings.db_name}' already exists.")
            return
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(settings.db_name)))
        print(f"Created database '{settings.db_name}'.")


def run_sql_file(sql_file: Path) -> None:
    """Run every statement in a .sql file inside the CampusFix database."""
    sql_text = sql_file.read_text(encoding="utf-8")
    with connect_to(settings.db_name) as connection:
        connection.execute(sql_text)
    print(f"Ran {sql_file.name}.")


def main() -> None:
    """Create the database, then the tables, then the sample data."""
    print(f"Connecting to PostgreSQL at {settings.db_host}:{settings.db_port} as '{settings.db_user}'...")
    create_database_if_missing()
    run_sql_file(SCHEMA_FILE)
    run_sql_file(SEED_FILE)
    print("Done. Start the server with:  uvicorn app.main:app --reload")


if __name__ == "__main__":
    try:
        main()
    except psycopg.OperationalError as connection_error:
        print("\nCould not connect to PostgreSQL.")
        print("Check that PostgreSQL is running and that DB_PASSWORD in backend/.env is correct.")
        print(f"Details: {connection_error}")
        raise SystemExit(1)
