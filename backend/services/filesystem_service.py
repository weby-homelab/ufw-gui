"""
UFW-GUI - Filesystem service
Handles snapshot management, users, and configuration files
"""
import os
import json
import shutil
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
    if not os.path.exists(USER_DATA_FILE):
        return {}
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f)


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
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)


# --- Snapshots ---

def create_snapshot(label: str = "auto") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join([c if c.isalnum() else "_" for c in label])
    snap_path = os.path.join(UFW_BACKUP_DIR, f"snap_{ts}_{safe_label}")
    if os.path.exists("/etc/ufw"):
        shutil.copytree("/etc/ufw", snap_path, dirs_exist_ok=True)
    return ts


def list_snapshots() -> list:
    if not os.path.exists(UFW_BACKUP_DIR):
        return []
    return sorted(os.listdir(UFW_BACKUP_DIR), reverse=True)


def restore_snapshot(name: str) -> bool:
    safe_name = os.path.basename(name)
    if not safe_name or safe_name.startswith("."):
        raise ValueError("Invalid snapshot name")

    snap_path = os.path.realpath(os.path.join(UFW_BACKUP_DIR, safe_name))
    base_dir = os.path.realpath(UFW_BACKUP_DIR)

    if not snap_path.startswith(base_dir + os.sep):
        raise ValueError("Path traversal detected")

    if not os.path.exists(snap_path):
        raise FileNotFoundError("Snapshot not found")

    shutil.copytree(snap_path, "/etc/ufw", dirs_exist_ok=True)
    return True


def get_test_rollback_path() -> str:
    return os.path.join(UFW_BACKUP_DIR, "test_rollback_config")


def save_test_rollback():
    fallback_path = get_test_rollback_path()
    if os.path.exists(fallback_path):
        if os.path.isdir(fallback_path):
            shutil.rmtree(fallback_path)
        else:
            os.remove(fallback_path)

    if os.path.exists("/etc/ufw"):
        shutil.copytree("/etc/ufw", fallback_path, dirs_exist_ok=True)
