"""
UFW-GUI - Admin, settings, and snapshots router
"""

import logging
import sqlite3

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.services.auth_service import get_current_user, hash_password
from backend.services.database_service import get_audit_logs, log_action
from backend.services.filesystem_service import (
    SNAPSHOT_RESTORE_UNAVAILABLE,
    create_regular_user,
    delete_user_record,
    list_snapshots,
    load_config,
    load_users,
    save_config,
)
from backend.services.recovery_guard import (
    protect_firewall_mutation,
)
from backend.utils.validators import is_valid_new_password, is_valid_username

current_user_dependency = Depends(get_current_user)

router = APIRouter(prefix="/api", tags=["Admin"])
logger = logging.getLogger(__name__)


class SettingsSchema(BaseModel):
    tg_token: str | None = Field(default=None, max_length=100)
    tg_chat_id: str | None = Field(default=None, max_length=50)

    model_config = {
        "extra": "ignore",
    }


# === Audit Logs ===


@router.get("/audit-logs")
async def get_audit(user=current_user_dependency):
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403)
    try:
        logs = get_audit_logs()
        return {"logs": logs}
    except sqlite3.Error as exc:
        logger.warning("Could not load audit logs (%s).", type(exc).__name__)
        return {"logs": []}


# === Users ===


@router.get("/users")
async def get_users(user=current_user_dependency):
    if user["role"] != "superadmin":
        raise HTTPException(status_code=403)
    users = load_users()
    return [
        {"username": name, "role": data.get("role")} for name, data in users.items()
    ]


@router.post("/users")
async def add_user(
    username: str = Body(..., max_length=64),
    password: str = Body(..., max_length=72),
    user=current_user_dependency,
):
    if user["role"] != "superadmin":
        raise HTTPException(status_code=403)
    if len(username) > 64 or not is_valid_username(username):
        raise HTTPException(status_code=400, detail="Invalid username")
    if not is_valid_new_password(password):
        raise HTTPException(status_code=400, detail="Invalid password length")

    # Preserve legacy-user migration, but never use a stale snapshot for writes.
    load_users()
    result = create_regular_user(user["username"], username, hash_password(password))
    if result == "forbidden":
        raise HTTPException(status_code=403)
    if result == "exists":
        raise HTTPException(status_code=409, detail="User already exists")
    log_action(user["username"], "ADD_USER", username)
    return {"status": "success"}


@router.delete("/users/{username}")
async def del_user(username: str, user=current_user_dependency):
    if user["role"] != "superadmin":
        raise HTTPException(status_code=403)

    if user["username"] == username:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    # Preserve legacy-user migration; the transaction rechecks all authorization.
    load_users()
    result = delete_user_record(user["username"], username)
    if result == "forbidden":
        raise HTTPException(status_code=403)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="User not found")
    if result == "self":
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if result == "last_superadmin":
        raise HTTPException(status_code=400, detail="Cannot delete the only superadmin")
    log_action(user["username"], "DEL_USER", username)
    return {"status": "success"}


# === Settings ===


@router.get("/settings")
async def get_settings(user=current_user_dependency):
    if user["role"] != "superadmin":
        raise HTTPException(status_code=403)
    config = load_config()
    return {
        "tg_token_configured": bool(config.get("tg_token")),
        "tg_chat_id": config.get("tg_chat_id", ""),
    }


@router.post("/settings")
async def save_settings(
    data: SettingsSchema,
    user=current_user_dependency,
):
    if user["role"] != "superadmin":
        raise HTTPException(status_code=403)
    try:
        settings = load_config()
        if data.tg_token:
            settings["tg_token"] = data.tg_token
        if "tg_chat_id" in data.model_fields_set:
            settings["tg_chat_id"] = data.tg_chat_id
        save_config(settings)
        return {"status": "success"}
    except OSError as exc:
        logger.error("Could not save settings (%s).", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to save settings")


# === Snapshots ===


@router.get("/snapshots/all")
async def get_snapshots(user=current_user_dependency):
    snaps = list_snapshots()
    return {"snapshots": [s for s in snaps if not s.startswith("test_")]}


@router.post("/snapshots/restore/{name}")
@protect_firewall_mutation
async def restore_snapshot_route(
    name: str,
    user=current_user_dependency,
):
    del name
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin role required")
    raise HTTPException(status_code=503, detail=SNAPSHOT_RESTORE_UNAVAILABLE)
