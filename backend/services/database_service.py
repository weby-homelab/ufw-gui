"""
UFW-GUI - Database service
Handles SQLite operations for drops and audit logs
"""

import fcntl
import json
import logging
import os
import secrets
import sqlite3
import stat
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
from pathlib import Path

import requests

from backend.services.sqlite_utils import (
    connect_existing_database,
    has_valid_application_schema,
)

logger = logging.getLogger(__name__)

DATA_DIR = "/app/data"
DB_FILE = f"{DATA_DIR}/stats.db"

# Expose a thread pool executor with maximum 2 threads to queue/throttling alerts
_tg_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tg_alerts")

_TRUSTED_STORAGE_IDENTITIES: dict[str, tuple[int, int, int, int]] = {}


def trusted_storage_identity(data_directory: str) -> tuple[int, int, int, int] | None:
    """Return this process's startup-validated directory/database inode pair."""
    return _TRUSTED_STORAGE_IDENTITIES.get(os.path.abspath(data_directory))


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE drops
        (id INTEGER PRIMARY KEY, ts TIMESTAMP, src TEXT, proto TEXT, port TEXT,
         UNIQUE(ts, src, port))
    """)
    connection.execute("""
        CREATE TABLE audit_logs
        (id INTEGER PRIMARY KEY, ts TIMESTAMP, username TEXT, action TEXT, details TEXT)
    """)
    connection.execute("""
        CREATE TABLE users
        (username TEXT PRIMARY KEY, password TEXT, role TEXT)
    """)


def _has_required_schema(connection: sqlite3.Connection) -> bool:
    return has_valid_application_schema(connection)


def initialize_empty_database() -> None:
    """Provision a brand-new data store explicitly; never overwrite an existing DB."""
    data_directory = os.path.dirname(os.path.abspath(DB_FILE))
    directory_fd = None
    database_fd = None
    temporary_name = None
    try:
        directory_fd = os.open(
            data_directory,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        directory_metadata = os.fstat(directory_fd)
        if (
            not stat.S_ISDIR(directory_metadata.st_mode)
            or directory_metadata.st_mode & 0o022
        ):
            raise RuntimeError("Persistent application data directory is unsafe")
        path_metadata = os.stat(data_directory, follow_symlinks=False)
        if (directory_metadata.st_dev, directory_metadata.st_ino) != (
            path_metadata.st_dev,
            path_metadata.st_ino,
        ):
            raise RuntimeError("Persistent application data directory changed")

        try:
            fcntl.flock(directory_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Application storage is already locked") from exc

        if os.listdir(directory_fd):
            raise RuntimeError(
                "Refusing to initialize a non-empty application data directory"
            )

        temporary_name = f".stats.db-init-{secrets.token_hex(16)}.tmp"
        database_fd = os.open(
            temporary_name,
            os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        temporary_path = f"/proc/self/fd/{directory_fd}/{temporary_name}"
        with closing(sqlite3.connect(temporary_path)) as connection, connection:
            connection.execute("PRAGMA journal_mode=MEMORY;")
            _create_schema(connection)

        os.fsync(database_fd)
        path_metadata = os.stat(data_directory, follow_symlinks=False)
        if (directory_metadata.st_dev, directory_metadata.st_ino) != (
            path_metadata.st_dev,
            path_metadata.st_ino,
        ):
            raise RuntimeError("Persistent application data directory changed")
        if os.listdir(directory_fd) != [temporary_name]:
            raise RuntimeError(
                "Application storage changed during database initialization"
            )

        # Relative hard-link publication is atomic and never follows path aliases.
        os.link(
            temporary_name,
            "stats.db",
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
            follow_symlinks=False,
        )
        os.fsync(directory_fd)
    except FileExistsError as exc:
        raise RuntimeError(
            "Refusing to replace an existing application database"
        ) from exc
    except (OSError, sqlite3.Error) as exc:
        raise RuntimeError(
            "Could not initialize persistent application database"
        ) from exc
    finally:
        if directory_fd is not None:
            if temporary_name is not None:
                try:
                    os.unlink(temporary_name, dir_fd=directory_fd)
                    os.fsync(directory_fd)
                except FileNotFoundError:
                    pass
            if database_fd is not None:
                os.close(database_fd)
            try:
                fcntl.flock(directory_fd, fcntl.LOCK_UN)
            finally:
                os.close(directory_fd)


def init_db():
    database_path = os.path.abspath(DB_FILE)
    data_directory = os.path.dirname(database_path)
    _TRUSTED_STORAGE_IDENTITIES.pop(data_directory, None)
    try:
        directory_metadata = os.lstat(data_directory)
        metadata = os.lstat(database_path)
    except OSError as exc:
        raise RuntimeError("Persistent application database is unavailable") from exc
    if (
        not stat.S_ISDIR(directory_metadata.st_mode)
        or directory_metadata.st_mode & 0o022
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_mode & 0o022
    ):
        raise RuntimeError("Persistent application database is unsafe")

    database_uri = f"{Path(database_path).as_uri()}?mode=rw"
    try:
        with closing(sqlite3.connect(database_uri, uri=True)) as conn:
            if not _has_required_schema(conn):
                raise RuntimeError(
                    "Persistent application database schema is incomplete"
                )
            integrity = conn.execute("PRAGMA quick_check(1)").fetchone()
            if integrity != ("ok",):
                raise RuntimeError("Persistent application database is corrupt")
    except sqlite3.Error as exc:
        raise RuntimeError("Persistent application database is invalid") from exc

    current_directory = os.stat(data_directory, follow_symlinks=False)
    current_database = os.stat(database_path, follow_symlinks=False)
    expected = (
        directory_metadata.st_dev,
        directory_metadata.st_ino,
        metadata.st_dev,
        metadata.st_ino,
    )
    current = (
        current_directory.st_dev,
        current_directory.st_ino,
        current_database.st_dev,
        current_database.st_ino,
    )
    if current != expected:
        raise RuntimeError("Persistent application storage changed during validation")
    _TRUSTED_STORAGE_IDENTITIES[data_directory] = expected


def log_action(username: str, action: str, details: str):
    try:
        with closing(connect_existing_database(DB_FILE)) as conn, conn:
            conn.execute(
                "INSERT INTO audit_logs (ts, username, action, details) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), username, action, str(details)),
            )
    except sqlite3.Error as exc:
        logger.error("Failed to save action to audit log (%s).", type(exc).__name__)

    try:
        # Submit Telegram alert task to thread pool instead of spawning a new OS thread
        _tg_executor.submit(_send_tg_alert, username, action, details)
    except RuntimeError as exc:
        logger.error("Failed to submit Telegram alert (%s).", type(exc).__name__)


def shutdown_db():
    _tg_executor.shutdown(wait=False)


def _send_tg_alert(username: str, action: str, details: str):
    config_file = f"{DATA_DIR}/config.json"
    try:
        if not os.path.exists(config_file):
            return
        with open(config_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        logger.error(
            "Could not load Telegram alert configuration (%s).", type(exc).__name__
        )
        return

    if not isinstance(cfg, dict):
        logger.warning("Telegram alert configuration has an invalid structure.")
        return

    token = cfg.get("tg_token")
    chat_id = cfg.get("tg_chat_id")
    if (
        not isinstance(token, str)
        or not token
        or not isinstance(chat_id, str)
        or not chat_id
    ):
        return

    text = f"🛡️ *UFW Action*\n👤 User: {username}\n🎯 Action: {action}\n📝 Details: {details}"
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=5,
        )
        response.raise_for_status()
    except (requests.RequestException, ValueError) as exc:
        # Request exceptions may contain the bot-token URL; log only the class.
        logger.error("Failed to send Telegram alert (%s).", type(exc).__name__)


def get_recent_drops(limit: int = 500) -> list:
    conn = connect_existing_database(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM drops WHERE ts > datetime('now', '-24 hours') ORDER BY ts DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stats_last_24h() -> list:
    conn = connect_existing_database(DB_FILE)
    query = """
        SELECT strftime('%H:', ts) || (CAST(strftime('%M', ts) AS INTEGER) / 10) || '0' as interval, 
               count(*) as count
        FROM drops 
        WHERE ts > datetime('now', '-24 hours') 
        GROUP BY interval 
        ORDER BY interval ASC
    """
    res = conn.execute(query).fetchall()
    conn.close()
    return [{"hour": r[0], "count": r[1]} for r in res]


def get_audit_logs(limit: int = 50) -> list:
    conn = connect_existing_database(DB_FILE)
    rows = conn.execute(
        "SELECT ts, username, action, details FROM audit_logs ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [{"ts": r[0], "user": r[1], "action": r[2], "details": r[3]} for r in rows]
