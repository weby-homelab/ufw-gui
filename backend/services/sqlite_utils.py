"""Safe SQLite connection helpers for the persistent application database."""

import os
import sqlite3
import stat
from pathlib import Path

_APPLICATION_TABLES = {
    "drops": {
        "id": ("INTEGER", 1),
        "ts": ("TIMESTAMP", 0),
        "src": ("TEXT", 0),
        "proto": ("TEXT", 0),
        "port": ("TEXT", 0),
    },
    "audit_logs": {
        "id": ("INTEGER", 1),
        "ts": ("TIMESTAMP", 0),
        "username": ("TEXT", 0),
        "action": ("TEXT", 0),
        "details": ("TEXT", 0),
    },
    "users": {
        "username": ("TEXT", 1),
        "password": ("TEXT", 0),
        "role": ("TEXT", 0),
    },
}


def has_valid_application_schema(connection: sqlite3.Connection) -> bool:
    """Validate the expected columns, primary keys, and uniqueness constraints."""
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if not set(_APPLICATION_TABLES).issubset(tables):
        return False

    for table, expected_columns in _APPLICATION_TABLES.items():
        actual_columns = {
            row[1]: (row[2].upper(), row[5])
            for row in connection.execute(f'PRAGMA table_info("{table}")')
        }
        if actual_columns != expected_columns:
            return False

    unique_drop_indexes = set()
    for index in connection.execute('PRAGMA index_list("drops")'):
        if not index[2] or index[4]:
            continue
        escaped_name = index[1].replace('"', '""')
        unique_drop_indexes.add(
            tuple(
                row[2]
                for row in connection.execute(f'PRAGMA index_info("{escaped_name}")')
            )
        )
    if ("ts", "src", "port") not in unique_drop_indexes:
        return False

    placeholders = ",".join("?" for _ in _APPLICATION_TABLES)
    trigger = connection.execute(
        f"SELECT 1 FROM sqlite_master WHERE type = 'trigger' "
        f"AND tbl_name IN ({placeholders}) LIMIT 1",
        tuple(_APPLICATION_TABLES),
    ).fetchone()
    return trigger is None


def connect_existing_database(path: str) -> sqlite3.Connection:
    """Open an existing regular database without SQLite's create-on-open behavior."""
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise sqlite3.OperationalError("Persistent database is unavailable") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise sqlite3.OperationalError("Persistent database is not a regular file")

    uri = f"{Path(os.path.abspath(path)).as_uri()}?mode=rw"
    return sqlite3.connect(uri, uri=True)
