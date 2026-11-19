"""PostgreSQL connection helpers.

Every helper opens a connection, runs ONE query with %s placeholders
(parameterized, so user input can never change the SQL) and closes it again.
Rows come back as Python dictionaries, e.g. {"id": 1, "title": "Wi-Fi down"}.
"""

from typing import Any, Optional, Sequence

import psycopg
from psycopg.rows import dict_row

from app.config import settings


def get_connection() -> psycopg.Connection:
    """Open a new connection to the CampusFix database (rows are returned as dicts)."""
    return psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        row_factory=dict_row,
    )


def fetch_one_row(query: str, parameters: Sequence[Any] = ()) -> Optional[dict]:
    """Run a query and return the first row, or None when nothing matches.

    Also used for INSERT/UPDATE ... RETURNING queries; the change is committed.
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return cursor.fetchone()


def fetch_all_rows(query: str, parameters: Sequence[Any] = ()) -> list[dict]:
    """Run a query and return all matching rows as a list of dicts."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return cursor.fetchall()


def execute_query(query: str, parameters: Sequence[Any] = ()) -> int:
    """Run an INSERT/UPDATE/DELETE query, commit it and return how many rows changed."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return cursor.rowcount
