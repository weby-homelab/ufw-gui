"""
UFW-GUI - FastAPI Application Entry Point
Imports and registers all routers, configures middleware, serves frontend.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.routers.admin_router import router as admin_router

# --- Import Routers ---
from backend.routers.auth_router import router as auth_router
from backend.routers.fail2ban_router import router as f2b_router
from backend.routers.logs_router import router as logs_router
from backend.routers.reload_router import router as reload_router
from backend.routers.ufw_router import router as ufw_router
from backend.services.database_service import init_db, shutdown_db
from backend.services.filesystem_service import init_dirs
from backend.services.log_parser_service import start_log_parser
from backend.services.recovery_guard import (
    has_unresolved_recovery_marker,
    recovery_state_lock,
)
from backend.services.system_diagnostics import collect_diagnostics

# --- File Whitelist (breaks CodeQL taint flow) ---
ALLOWED_FILES: dict[str, str] = {}
logger = logging.getLogger(__name__)


def _build_file_whitelist():
    """Build a whitelist of allowed static files at startup to break CodeQL taint flow.

    User input is used ONLY as a dictionary key lookup. The actual file paths
    originate from os.walk() at startup, never from composing user input into
    a path expression. This completely severs the taint chain.
    """
    base = "/app/static"
    if not os.path.exists(base):
        return
    real_base = os.path.realpath(base)
    for root, _dirs, files in os.walk(real_base):
        for fname in files:
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, real_base)
            ALLOWED_FILES[rel] = full


_build_file_whitelist()


async def inspect_recovery_state_on_startup():
    logger = logging.getLogger(__name__)
    async with recovery_state_lock():
        unresolved = has_unresolved_recovery_marker()

    if unresolved:
        logger.error(
            "Unresolved firewall recovery marker found; automatic recovery is disabled. "
            "Preserving marker and configuration; operator manual recovery is required."
        )
        return
    logger.info(
        "No unresolved recovery marker; automatic firewall recovery is disabled."
    )


async def ensure_persistent_storage_validated(app: FastAPI) -> None:
    """Validate trusted storage before every request, including with lifespan off."""
    async with app.state.storage_validation_lock:
        app.state.storage_validated = False
        if not app.state.storage_initialized:
            if app.state.storage_initialization_attempted:
                raise RuntimeError(
                    "Persistent storage initialization previously failed"
                )
            # Never bind a newly appeared database after a failed initial check
            # in this process. An operator must inspect storage and restart it.
            app.state.storage_initialization_attempted = True
            init_dirs()
            init_db()
            # Keep the startup binding even if marker inspection fails: never
            # silently trust a replacement database later in this process.
            app.state.storage_initialized = True
            await inspect_recovery_state_on_startup()
        else:
            await revalidate_persistent_storage()
        app.state.storage_validated = True


async def revalidate_persistent_storage() -> None:
    """Check the startup-bound database and marker without rebinding storage."""
    async with recovery_state_lock():
        has_unresolved_recovery_marker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.storage_validated = False
    await ensure_persistent_storage_validated(app)
    diagnostics = collect_diagnostics()
    for hint in diagnostics["hints"]:
        logger.warning("UFW integration: %s", hint)

    # Start background log parser for statistics
    parser_task = asyncio.create_task(start_log_parser())
    try:
        yield
    finally:
        # Clean up parser task on shutdown
        parser_task.cancel()
        try:
            await parser_task
        except asyncio.CancelledError:
            pass
        shutdown_db()
        app.state.storage_validated = False


app = FastAPI(
    title="UFW-GUI API",
    description="Modern firewall management for Linux via Docker",
    version="1.6.0",
    lifespan=lifespan,
)
app.state.storage_validation_lock = asyncio.Lock()
app.state.storage_validated = False
app.state.storage_initialized = False
app.state.storage_initialization_attempted = False


@app.middleware("http")
async def validate_storage_before_serving(
    request: Request,
    call_next,
) -> Response:
    try:
        await ensure_persistent_storage_validated(request.app)
    except (HTTPException, OSError, RuntimeError) as exc:
        logger.error("Persistent storage validation failed (%s).", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"detail": "Persistent recovery storage is unavailable"},
        )
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_error_without_input(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    # Validation inputs can contain passwords, Telegram tokens, or other secrets.
    errors = [
        {key: value for key, value in error.items() if key != "input"}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": errors}),
    )


# --- CORS Configuration ---
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not allowed_origins or allowed_origins == [""]:
    allowed_origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# --- Register Routers ---
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Report validated storage health, not firewall mutation readiness."""
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(ufw_router)
app.include_router(f2b_router)
app.include_router(logs_router)
app.include_router(admin_router)
app.include_router(reload_router)

# --- Static Files & SPA Fallback ---
if os.path.exists("/app/static"):
    if os.path.exists("/app/static/assets"):
        app.mount("/assets", StaticFiles(directory="/app/static/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)

        # Strip leading slash to get relative path for whitelist lookup.
        # User input is used ONLY as a dict key — it never composes into
        # a file path expression, which completely breaks CodeQL taint flow.
        rel_path = full_path.lstrip("/")

        if rel_path in ALLOWED_FILES:
            return FileResponse(ALLOWED_FILES[rel_path])

        # SPA fallback: serve index.html for any unmatched route
        index_path = os.path.join("/app/static", "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Not found")
