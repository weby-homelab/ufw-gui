"""
UFW-GUI - Admin, settings, and snapshots router
"""
from fastapi import APIRouter, Body, Depends, HTTPException
from typing import Any
from pydantic import BaseModel, Field


class SettingsSchema(BaseModel):
    tg_token: str | None = Field(default=None, max_length=100)
    tg_chat_id: str | None = Field(default=None, max_length=50)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "tg_token": "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ",
                "tg_chat_id": "-100123456789"
            }
        }
    }

from backend.services.auth_service import get_current_user, hash_password
from backend.services.filesystem_service import (
    load_users, save_users, load_config, save_config,
    list_snapshots, restore_snapshot, get_test_rollback_path,
    save_test_rollback, init_dirs,
)
from backend.services.subprocess_service import run_ufw
from backend.services.database_service import log_action, get_audit_logs
from backend.utils.validators import is_valid_username

router = APIRouter(prefix="/api", tags=["Admin"])


# === Audit Logs ===

@router.get("/audit-logs")
async def get_audit(user=Depends(get_current_user)):
    try:
        logs = get_audit_logs()
        return {"logs": logs}
    except Exception:
        return {"logs": []}


# === Users ===

@router.get("/users")
async def get_users(user=Depends(get_current_user)):
    if user["role"] != "superadmin":
        raise HTTPException(status_code=403)
    users = load_users()
    return [{"username": name, "role": data.get("role")} for name, data in users.items()]


@router.post("/users")
async def add_user(
    username: str = Body(...),
    password: str = Body(...),
    user=Depends(get_current_user),
):
    if user["role"] != "superadmin":
        raise HTTPException(status_code=403)
    if not is_valid_username(username):
        raise HTTPException(status_code=400, detail="Invalid username")

    users = load_users()
    users[username] = {"password": hash_password(password), "role": "admin"}
    save_users(users)
    log_action(user["username"], "ADD_USER", username)
    return {"status": "success"}


@router.delete("/users/{username}")
async def del_user(username: str, user=Depends(get_current_user)):
    if user["role"] != "superadmin":
        raise HTTPException(status_code=403)
    
    if user["username"] == username:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    users = load_users()
    if username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    
    if users[username].get("role") == "superadmin":
        superadmins = [name for name, u_data in users.items() if u_data.get("role") == "superadmin"]
        if len(superadmins) <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the only superadmin")

    del users[username]
    save_users(users)
    log_action(user["username"], "DEL_USER", username)
    return {"status": "success"}


# === Settings ===

@router.get("/settings")
async def get_settings(user=Depends(get_current_user)):
    try:
        return load_config()
    except Exception:
        return {}


@router.post("/settings")
async def save_settings(
    data: SettingsSchema,
    user=Depends(get_current_user),
):
    if user["role"] != "superadmin":
        raise HTTPException(status_code=403)
    try:
        save_config(data.model_dump())
        return {"status": "success"}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save settings")


# === Snapshots ===

@router.get("/snapshots/all")
async def get_snapshots(user=Depends(get_current_user)):
    snaps = list_snapshots()
    return {"snapshots": [s for s in snaps if not s.startswith("test_")]}


@router.post("/snapshots/restore/{name}")
async def restore_snapshot_route(
    name: str,
    user=Depends(get_current_user),
):
    try:
        await restore_snapshot(name)
        await run_ufw("reload")
        log_action(user["username"], "RESTORE", name)
        return {"status": "success"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to restore snapshot")
