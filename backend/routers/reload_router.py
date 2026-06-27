"""
UFW-GUI - Test reload router
Handles 60-second test mode with auto-rollback
"""
import asyncio
from fastapi import APIRouter, Depends
import shutil
import os

from backend.services.auth_service import get_current_user
from backend.services.subprocess_service import run_ufw
from backend.services.filesystem_service import (
    save_test_rollback,
    get_test_rollback_path,
    UFW_BACKUP_DIR,
)
from backend.services.database_service import log_action
from backend.utils.validators import validate_args

router = APIRouter(prefix="/api/reload", tags=["Test Mode"])


rollback_task_ref = None


async def perform_rollback():
    await asyncio.sleep(60)
    fallback_path = get_test_rollback_path()
    if os.path.exists(fallback_path):
        shutil.copytree(fallback_path, "/etc/ufw", dirs_exist_ok=True)
        run_ufw("reload")
        log_action("SYSTEM", "ROLLBACK", "Auto-reverted untested changes after 60s")


@router.post("/test")
async def reload_test(user=Depends(get_current_user)):
    global rollback_task_ref

    if rollback_task_ref and not rollback_task_ref.done():
        rollback_task_ref.cancel()

    os.makedirs(UFW_BACKUP_DIR, exist_ok=True)
    save_test_rollback()

    res = run_ufw("reload")
    log_action(user["username"], "TEST_RELOAD", "Testing firewall changes for 60s")

    rollback_task_ref = asyncio.create_task(perform_rollback())
    return {"status": "testing", "result": res}


@router.post("/confirm")
async def reload_confirm(user=Depends(get_current_user)):
    global rollback_task_ref

    if rollback_task_ref and not rollback_task_ref.done():
        rollback_task_ref.cancel()
        log_action(user["username"], "CONFIRM", "Changes confirmed")
        return {"status": "confirmed"}
    return {"status": "no_active_test"}
