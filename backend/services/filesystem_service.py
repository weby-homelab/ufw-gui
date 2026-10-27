"""
UFW-GUI - Filesystem service
Handles snapshot management, users, and configuration files
"""

import json
import logging
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Literal

from fastapi import HTTPException

from backend.services.sqlite_utils import (
    connect_existing_database,
    has_valid_application_schema,
)

DATA_DIR = "/app/data"
USER_DATA_FILE = f"{DATA_DIR}/users.json"
CONFIG_FILE = f"{DATA_DIR}/config.json"
UFW_BACKUP_DIR = f"{DATA_DIR}/ufw_backups"
TEST_STATE_FILE = f"{DATA_DIR}/test_state.json"
logger = logging.getLogger(__name__)


def init_dirs():
    try:
        metadata = os.lstat(DATA_DIR)
    except OSError as exc:
        raise RuntimeError(
            "Persistent application data directory is unavailable"
        ) from exc
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_mode & 0o022:
        raise RuntimeError("Persistent application data directory is unsafe")


def _application_database_is_valid(
    directory_fd: int | None = None,
    database_fd: int | None = None,
) -> bool:
    """Require the persistent database schema as evidence of initialized storage."""
    data_dir = os.path.dirname(os.path.abspath(TEST_STATE_FILE))
    database_path = os.path.join(data_dir, "stats.db")
    opened_database_fd = None
    try:
        if database_fd is not None:
            metadata = os.fstat(database_fd)
            database_uri = f"file:/proc/self/fd/{database_fd}?mode=ro"
        elif directory_fd is None:
            metadata = os.lstat(database_path)
            database_uri = f"{Path(database_path).as_uri()}?mode=ro"
        else:
            entry_metadata = os.stat(
                "stats.db", dir_fd=directory_fd, follow_symlinks=False
            )
            opened_database_fd = os.open(
                "stats.db",
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=directory_fd,
            )
            metadata = os.fstat(opened_database_fd)
            if (entry_metadata.st_dev, entry_metadata.st_ino) != (
                metadata.st_dev,
                metadata.st_ino,
            ):
                return False
            database_uri = f"file:/proc/self/fd/{opened_database_fd}?mode=ro"
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o022:
            return False
        with closing(sqlite3.connect(database_uri, uri=True)) as connection:
            if not has_valid_application_schema(connection):
                return False
            if connection.execute("PRAGMA quick_check(1)").fetchone() != ("ok",):
                return False
        if opened_database_fd is not None:
            entry_metadata = os.stat(
                "stats.db", dir_fd=directory_fd, follow_symlinks=False
            )
            metadata = os.fstat(opened_database_fd)
            if (entry_metadata.st_dev, entry_metadata.st_ino) != (
                metadata.st_dev,
                metadata.st_ino,
            ):
                return False
    except (OSError, sqlite3.Error, ValueError):
        return False
    finally:
        if opened_database_fd is not None:
            os.close(opened_database_fd)
    return True


# --- Users ---


def load_users() -> dict:
    db_path = os.path.join(DATA_DIR, "stats.db")
    if not os.path.exists(db_path):
        raise RuntimeError("User database is unavailable")

    # Migration commits all records together; on failure, keep the source file
    # and propagate the error instead of allowing unauthenticated setup.
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r", encoding="utf-8") as source:
            legacy_users = json.load(source)
        with closing(connect_existing_database(db_path)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            for username, data in legacy_users.items():
                conn.execute(
                    "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, data["password"], data.get("role", "admin")),
                )
        os.remove(USER_DATA_FILE)

    # Explicitly close connections even if reading fails.
    with closing(connect_existing_database(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT username, password, role FROM users").fetchall()
    return {r["username"]: {"password": r["password"], "role": r["role"]} for r in rows}


def create_initial_admin(username: str, password_hash: str) -> bool:
    """Create the first admin atomically; never overwrite existing accounts."""
    db_path = os.path.join(DATA_DIR, "stats.db")
    if not os.path.exists(db_path):
        raise RuntimeError("User database is unavailable")
    conn = connect_existing_database(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            conn.rollback()
            return False
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, password_hash, "superadmin"),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_regular_user(
    actor: str, username: str, password_hash: str
) -> Literal["created", "forbidden", "exists"]:
    """Create one user after rechecking the actor under a write transaction."""
    database_path = os.path.join(DATA_DIR, "stats.db")
    with closing(connect_existing_database(database_path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        actor_row = conn.execute(
            "SELECT role FROM users WHERE username = ?", (actor,)
        ).fetchone()
        if actor_row is None or actor_row[0] != "superadmin":
            return "forbidden"
        existing = conn.execute(
            "SELECT 1 FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            return "exists"
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, password_hash, "admin"),
        )
        return "created"


def delete_user_record(
    actor: str, username: str
) -> Literal["deleted", "forbidden", "not_found", "self", "last_superadmin"]:
    """Delete one user without allowing stale snapshots to resurrect accounts."""
    database_path = os.path.join(DATA_DIR, "stats.db")
    with closing(connect_existing_database(database_path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        actor_row = conn.execute(
            "SELECT role FROM users WHERE username = ?", (actor,)
        ).fetchone()
        if actor_row is None or actor_row[0] != "superadmin":
            return "forbidden"
        if actor == username:
            return "self"
        target = conn.execute(
            "SELECT role FROM users WHERE username = ?", (username,)
        ).fetchone()
        if target is None:
            return "not_found"
        if target[0] == "superadmin":
            count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'superadmin'"
            ).fetchone()[0]
            if count <= 1:
                return "last_superadmin"
        conn.execute("DELETE FROM users WHERE username = ?", (username,))
        return "deleted"


def save_users(users: dict):
    DB_FILE = f"{DATA_DIR}/stats.db"
    conn = connect_existing_database(DB_FILE)
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("DELETE FROM users")
        for username, data in users.items():
            conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, data["password"], data.get("role", "admin")),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- Config ---


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        if isinstance(config, dict):
            return config
        logger.warning("Configuration file has an invalid top-level structure.")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        logger.warning("Could not load configuration (%s).", type(exc).__name__)
        return {}
    return {}


def save_config(data: dict):
    fd, temp_path = tempfile.mkstemp(dir=DATA_DIR, prefix="config_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(temp_path, CONFIG_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


# --- Snapshots ---

SNAPSHOT_CREATION_UNAVAILABLE = (
    "snapshot_creation_unavailable: automatic snapshots are disabled; "
    "firewall changes apply immediately and must be verified manually."
)
SNAPSHOT_RESTORE_UNAVAILABLE = (
    "snapshot_restore_unavailable: snapshot restore is disabled; "
    "inspect legacy snapshots and recover the firewall manually."
)


async def create_snapshot(label: str = "auto") -> str:
    del label
    raise HTTPException(status_code=503, detail=SNAPSHOT_CREATION_UNAVAILABLE)


def list_snapshots() -> list:
    if not os.path.exists(UFW_BACKUP_DIR):
        return []
    return sorted(os.listdir(UFW_BACKUP_DIR), reverse=True)


async def restore_snapshot(name: str) -> bool:
    """Refuse snapshot restore under the shared firewall recovery guard."""
    del name
    from backend.services.recovery_guard import firewall_mutation_guard

    async with firewall_mutation_guard():
        raise HTTPException(status_code=503, detail=SNAPSHOT_RESTORE_UNAVAILABLE)


def has_unresolved_test_marker(
    directory_fd: int | None = None,
    database_fd: int | None = None,
    database_validated: bool = False,
) -> bool:
    """Fail closed on unresolved markers or unavailable persistent recovery storage."""
    if not database_validated and not _application_database_is_valid(
        directory_fd, database_fd
    ):
        return True
    try:
        if directory_fd is None:
            os.lstat(TEST_STATE_FILE)
        else:
            os.stat(
                os.path.basename(TEST_STATE_FILE),
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
    except FileNotFoundError:
        if directory_fd is not None:
            return False
        data_dir = os.path.dirname(os.path.abspath(TEST_STATE_FILE))
        try:
            metadata = os.lstat(data_dir)
        except OSError:
            return True
        return not stat.S_ISDIR(metadata.st_mode)
    except OSError:
        return True
    return True
