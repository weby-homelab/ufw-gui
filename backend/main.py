"""
UFW-GUI - FastAPI Application Entry Point
Imports and registers all routers, configures middleware, serves frontend.
"""
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.services.database_service import init_db, log_action, shutdown_db
from backend.services.filesystem_service import init_dirs, get_test_state, get_test_rollback_path, clear_test_state
from backend.services.log_parser_service import start_log_parser
from backend.services.subprocess_service import run_ufw
# --- Import Routers ---
from backend.routers.auth_router import router as auth_router
from backend.routers.ufw_router import router as ufw_router
from backend.routers.fail2ban_router import router as f2b_router
from backend.routers.logs_router import router as logs_router
from backend.routers.admin_router import router as admin_router
from backend.routers.reload_router import router as reload_router
import shutil

# --- File Whitelist (breaks CodeQL taint flow) ---
ALLOWED_FILES: dict[str, str] = {}


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


async def check_and_rollback_on_startup():
    state = get_test_state()
    if state.get("status") == "testing":
        import logging
        logging.info("Interrupted firewall test detected. Performing auto-rollback...")
        fallback_path = get_test_rollback_path()
        if os.path.exists(fallback_path):
            try:
                if os.path.exists("/etc/ufw"):
                    await asyncio.to_thread(shutil.rmtree, "/etc/ufw")
                await asyncio.to_thread(shutil.copytree, fallback_path, "/etc/ufw")
                await run_ufw("reload")
                log_action("SYSTEM", "CRASH_ROLLBACK", "Detected interrupted test. Auto-reverted UFW config.")
                logging.info("Auto-rollback successful.")
            except Exception as e:
                logging.error(f"Failed to perform startup rollback: {str(e)}")
        clear_test_state()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize directories and database on startup
    init_dirs()
    init_db()

    # Check for interrupted test and roll back if needed
    await check_and_rollback_on_startup()

    # Start background log parser for statistics
    parser_task = asyncio.create_task(start_log_parser())
    yield

    # Clean up parser task on shutdown
    parser_task.cancel()
    try:
        await parser_task
    except asyncio.CancelledError:
        pass
    shutdown_db()


app = FastAPI(
    title="UFW-GUI API",
    description="Modern firewall management for Linux via Docker",
    version="1.6.0",
    lifespan=lifespan,
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
