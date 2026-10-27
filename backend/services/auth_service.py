"""
UFW-GUI - Authentication service
Handles JWT tokens, access + refresh tokens, and password hashing
"""

import os
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import PyJWTError as JWTError

SECRET_KEY = os.getenv("UFW_GUI_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("FATAL: UFW_GUI_SECRET_KEY environment variable is not set!")
try:
    _secret_key_bytes = len(SECRET_KEY.encode("utf-8"))
except UnicodeEncodeError:
    raise ValueError("FATAL: UFW_GUI_SECRET_KEY has invalid encoding!") from None
if _secret_key_bytes < 32:
    raise ValueError("FATAL: UFW_GUI_SECRET_KEY must contain at least 32 bytes!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 4 * 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
BCRYPT_ROUNDS = 12
# bcrypt only considers the first 72 bytes; reject longer inputs instead of
# silently truncating them.  Hashes written by older passlib versions use the
# same $2a$/$2b$/$2y$ formats and remain verifiable.
BCRYPT_MAX_BYTES = 72
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
token_dependency = Depends(oauth2_scheme)


def _password_bytes(password: str) -> bytes | None:
    if not isinstance(password, str):
        return None
    try:
        return password.encode("utf-8")
    except UnicodeEncodeError:
        return None


def create_access_token(username: str, role: str = "admin") -> str:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": username, "role": role, "exp": expire, "type": "access"},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_refresh_token(username: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {
            "sub": username,
            "exp": expire,
            "type": "refresh",
            "jti": secrets.token_urlsafe(16),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def verify_refresh_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash without passlib.

    passlib 1.7.4 reads ``bcrypt.__about__``, which was removed in bcrypt 4.1.
    The resulting AttributeError filled logs on newer images and is the reason
    this module talks to bcrypt directly.
    """
    if not isinstance(hashed_password, str) or not hashed_password:
        return False
    encoded = _password_bytes(plain_password)
    if encoded is None:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed_password.encode("ascii"))
    except (ValueError, TypeError, UnicodeError):
        # Malformed/unsupported hashes must fail closed, never raise a 500.
        return False


def hash_password(password: str) -> str:
    encoded = _password_bytes(password)
    if encoded is None:
        raise ValueError("Password must be valid UTF-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must not exceed {BCRYPT_MAX_BYTES} UTF-8 bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


async def get_current_user(token: str = token_dependency) -> dict:
    from backend.services.filesystem_service import load_users

    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    username = payload.get("sub")
    users = load_users()
    if not username or username not in users:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    return {"username": username, "role": users[username].get("role", "admin")}
