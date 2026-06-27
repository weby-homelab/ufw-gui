"""
UFW-GUI - Authentication router
"""
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from backend.services.auth_service import create_access_token, verify_password, get_current_user, hash_password
from backend.services.filesystem_service import load_users, save_users
from backend.services.database_service import log_action
from backend.utils.validators import is_valid_username

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.get("/setup-needed")
async def is_setup_needed():
    users = load_users()
    return {"setup_needed": len(users) == 0}


@router.post("/setup")
async def setup_admin(
    username: str = Body(...),
    password: str = Body(...),
):
    users = load_users()
    if len(users) > 0:
        raise HTTPException(status_code=400, detail="Admin already exists")

    if not is_valid_username(username):
        raise HTTPException(status_code=400, detail="Invalid username format")

    users[username] = {"password": hash_password(password), "role": "superadmin"}
    save_users(users)
    log_action(username, "SETUP", "Superadmin created")
    return {"status": "success"}


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    users = load_users()
    u = users.get(form_data.username)
    if not u or not verify_password(form_data.password, u["password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(form_data.username)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    return user
