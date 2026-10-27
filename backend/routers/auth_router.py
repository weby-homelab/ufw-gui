"""
UFW-GUI - Authentication router
"""

import os
import secrets

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

from backend.services.auth_service import (
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.services.database_service import log_action
from backend.services.filesystem_service import create_initial_admin, load_users
from backend.utils.validators import is_valid_new_password, is_valid_username

current_user_dependency = Depends(get_current_user)
password_form_dependency = Depends()

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.get("/setup-needed")
async def is_setup_needed():
    users = load_users()
    return {"setup_needed": len(users) == 0}


@router.post("/setup")
async def setup_admin(
    request: Request,
    username: str = Body(..., max_length=64),
    password: str = Body(..., min_length=12, max_length=72),
    setup_token: str = Body("", max_length=256),
):
    # Trust only the ASGI server's scheme, never a client-supplied header here.
    # A TLS-terminating proxy must be explicitly trusted by the ASGI server.
    if request.url.scheme != "https":
        raise HTTPException(status_code=403, detail="Admin setup requires HTTPS")
    configured = os.getenv("UFW_GUI_SETUP_TOKEN", "")
    if (
        not 32 <= len(configured) <= 256
        or not configured.isascii()
        or configured == SECRET_KEY
    ):
        raise HTTPException(status_code=503, detail="Admin setup is unavailable")
    if not setup_token.isascii() or not secrets.compare_digest(configured, setup_token):
        raise HTTPException(status_code=403, detail="Admin setup is not authorized")

    if len(username) > 64 or not is_valid_username(username):
        raise HTTPException(status_code=400, detail="Invalid username format")
    if not is_valid_new_password(password):
        raise HTTPException(status_code=400, detail="Invalid password length")

    users = load_users()
    if len(users) > 0:
        raise HTTPException(status_code=400, detail="Admin already exists")

    if not create_initial_admin(username, hash_password(password)):
        raise HTTPException(status_code=400, detail="Admin already exists")
    log_action(username, "SETUP", "Superadmin created")
    return {"status": "success"}


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = password_form_dependency):
    users = load_users()
    u = users.get(form_data.username)
    if not u or not verify_password(form_data.password, u["password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    role = u.get("role", "admin")
    access_token = create_access_token(form_data.username, role)
    refresh_token = create_refresh_token(form_data.username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_token(
    form_data: OAuth2PasswordRequestForm = password_form_dependency,
):
    from backend.services.auth_service import verify_refresh_token

    refresh = verify_refresh_token(form_data.password)
    if not refresh:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    username = refresh.get("sub")
    users = load_users()
    if username not in users:
        raise HTTPException(status_code=401, detail="User not found")

    role = users[username].get("role", "admin")
    new_access = create_access_token(username, role)
    new_refresh = create_refresh_token(username)
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.get("/me")
async def get_me(user=current_user_dependency):
    return user
