"""
UFW-GUI - Filesystem service
Handles snapshot management, users, and configuration files
"""
import os
import json
import shutil
import sqlite3
import tempfile
import asyncio
from datetime import datetime


DATA_DIR = "/app/data"
USER_DATA_FILE = f"{DATA_DIR}/users.json"
CONFIG_FILE = f"{DATA_DIR}/config.json"
UFW_BACKUP_DIR = f"{DATA_DIR}/ufw_backups"


def init_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UFW_BACKUP_DIR, exist_ok=True)


# --- Users ---

def load_users() -> dict:
    DB_FILE = f"{DATA_DIR}/stats.db"
    # Auto-migration if users.json exists
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r") as f:
                legacy_users = json.load(f)
            conn = sqlite3.connect(DB_FILE)
            conn.execute("BEGIN TRANSACTION")
            for username, data in legacy_users.items():
                conn.execute(
                    "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, data["password"], data.get("role", "admin"))
                )
            conn.commit()
            conn.close()
            os.remove(USER_DATA_FILE)
        except Exception:
            pass

    if not os.path.exists(DB_FILE):
        return {}
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT username, password, role FROM users").fetchall()
        conn.close()
        return {r["username"]: {"password": r["password"], "role": r["role"]} for r in rows}
    except Exception:
        return {}


def save_users(users: dict):
    DB_FILE = f"{DATA_DIR}/stats.db"
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("DELETE FROM users")
        for username, data in users.items():
            conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, data["password"], data.get("role", "admin"))
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# --- Config ---

def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=DATA_DIR, prefix="config_", suffix=".tmp")
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f)
        os.replace(temp_path, CONFIG_FILE)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e


# --- Snapshots ---

async def create_snapshot(label: str = "auto") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join([c if c.isalnum() else "_" for c in label])
    snap_path = os.path.join(UFW_BACKUP_DIR, f"snap_{ts}_{safe_label}")
    if os.path.exists("/etc/ufw"):
        await asyncio.to_thread(shutil.copytree, "/etc/ufw", snap_path, dirs_exist_ok=True)
    return ts


def list_snapshots() -> list:
    if not os.path.exists(UFW_BACKUP_DIR):
        return []
    return sorted(os.listdir(UFW_BACKUP_DIR), reverse=True)


async def restore_snapshot(name: str) -> bool:
    safe_name = os.path.basename(name)
    if not safe_name or safe_name.startswith("."):
        raise ValueError("Invalid snapshot name")

    snap_path = os.path.realpath(os.path.join(UFW_BACKUP_DIR, safe_name))
    base_dir = os.path.realpath(UFW_BACKUP_DIR)

    if not snap_path.startswith(base_dir + os.sep):
        raise ValueError("Path traversal detected")

    if not os.path.exists(snap_path):
        raise FileNotFoundError("Snapshot not found")

    if os.path.exists("/etc/ufw"):
        await asyncio.to_thread(shutil.rmtree, "/etc/ufw")
    await asyncio.to_thread(shutil.copytree, snap_path, "/etc/ufw")
    return True


def get_test_rollback_path() -> str:
    return os.path.join(UFW_BACKUP_DIR, "test_rollback_config")


async def save_test_rollback():
    fallback_path = get_test_rollback_path()
    if os.path.exists(fallback_path):
        if os.path.isdir(fallback_path):
            await asyncio.to_thread(shutil.rmtree, fallback_path)
        else:
            await asyncio.to_thread(os.remove, fallback_path)

    if os.path.exists("/etc/ufw"):
        await asyncio.to_thread(shutil.copytree, "/etc/ufw", fallback_path, dirs_exist_ok=True)


# --- Test State ---

TEST_STATE_FILE = f"{DATA_DIR}/test_state.json"


def get_test_state() -> dict:
    if not os.path.exists(TEST_STATE_FILE):
        return {}
    try:
        with open(TEST_STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_test_state(state: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=DATA_DIR, prefix="test_state_", suffix=".tmp")
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(state, f)
        os.replace(temp_path, TEST_STATE_FILE)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e


def clear_test_state():
    if os.path.exists(TEST_STATE_FILE):
        try:
            os.remove(TEST_STATE_FILE)
        except Exception:
            pass
