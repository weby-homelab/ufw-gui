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
    version="1.5.9",
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
    allow_methods=["*"],
    allow_headers=["*"],
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

        # Normalize path and prevent any relative directory traversal
        normalized_path = os.path.normpath(full_path)
        if normalized_path.startswith("..") or normalized_path.startswith("/"):
            raise HTTPException(status_code=403, detail="Invalid path")

        base_dir = os.path.abspath("/app/static")
        file_path = os.path.abspath(os.path.join(base_dir, normalized_path))

        # Strict containment check to avoid directory traversal
        if not (file_path == base_dir or file_path.startswith(base_dir + os.sep)):
            raise HTTPException(status_code=403, detail="Access Denied")

        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(base_dir, "index.html"))
