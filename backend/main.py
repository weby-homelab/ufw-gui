"""
UFW-GUI - FastAPI Application Entry Point
Imports and registers all routers, configures middleware, serves frontend.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.services.database_service import init_db
from backend.services.filesystem_service import init_dirs

# Initialize directories and database on startup
init_dirs()
init_db()

app = FastAPI(
    title="UFW-GUI API",
    description="Modern firewall management for Linux via Docker",
    version="1.5.6",
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

# --- Import and Register Routers ---
from backend.routers.auth_router import router as auth_router
from backend.routers.ufw_router import router as ufw_router
from backend.routers.fail2ban_router import router as f2b_router
from backend.routers.logs_router import router as logs_router
from backend.routers.admin_router import router as admin_router
from backend.routers.reload_router import router as reload_router

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

        import re
        match = re.match(r'^([a-zA-Z0-9_\-\./]*)$', full_path)
        if not match or ".." in full_path:
            raise HTTPException(status_code=403, detail="Invalid path")

        safe_path = match.group(1)
        base_dir = os.path.abspath("/app/static")
        file_path = os.path.abspath(os.path.join(base_dir, safe_path))

        if not file_path.startswith(base_dir):
            raise HTTPException(status_code=403, detail="Access Denied")

        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(base_dir, "index.html"))
