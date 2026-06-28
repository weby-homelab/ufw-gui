"""
UFW-GUI - Test reload router
Handles 60-second test mode with auto-rollback
"""
from fastapi import APIRouter, Depends, HTTPException
import shutil
import os
import asyncio
from datetime import datetime

from backend.services.auth_service import get_current_user
from backend.services.subprocess_service import run_ufw
from backend.services.filesystem_service import (
    save_test_rollback,
    get_test_rollback_path,
    UFW_BACKUP_DIR,
    get_test_state,
    save_test_state,
    clear_test_state,
)
from backend.services.database_service import log_action
from backend.utils.validators import validate_args

router = APIRouter(prefix="/api/reload", tags=["Test Mode"])


rollback_task_ref = None


async def perform_rollback():
    try:
        await asyncio.sleep(60)
        state = get_test_state()
        if state.get("status") == "testing":
            fallback_path = get_test_rollback_path()
            if os.path.exists(fallback_path):
                if os.path.exists("/etc/ufw"):
                    await asyncio.to_thread(shutil.rmtree, "/etc/ufw")
                await asyncio.to_thread(shutil.copytree, fallback_path, "/etc/ufw")
                await run_ufw("reload")
                log_action("SYSTEM", "ROLLBACK", "Auto-reverted untested changes after 60s")
            clear_test_state()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        import logging
        logging.error(f"Failed to auto-rollback firewall configuration: {str(e)}")


@router.post("/test")
async def reload_test(user=Depends(get_current_user)):
    global rollback_task_ref

    # Check persistent test state to block parallel tests
    state = get_test_state()
    if state.get("status") == "testing":
        raise HTTPException(status_code=400, detail="Another test is already in progress")

    if rollback_task_ref and not rollback_task_ref.done():
        rollback_task_ref.cancel()

    os.makedirs(UFW_BACKUP_DIR, exist_ok=True)
    await save_test_rollback()

    # Save persistent state before applying changes
    save_test_state({"status": "testing", "started_at": datetime.now().isoformat()})

    res = await run_ufw("reload")
    log_action(user["username"], "TEST_RELOAD", "Testing firewall changes for 60s")

    rollback_task_ref = asyncio.create_task(perform_rollback())
    return {"status": "testing", "result": res}


@router.post("/confirm")
async def reload_confirm(user=Depends(get_current_user)):
    global rollback_task_ref

    state = get_test_state()
    if state.get("status") == "testing" or (rollback_task_ref and not rollback_task_ref.done()):
        if rollback_task_ref and not rollback_task_ref.done():
            rollback_task_ref.cancel()
        clear_test_state()
        log_action(user["username"], "CONFIRM", "Changes confirmed")
        return {"status": "confirmed"}
    return {"status": "no_active_test"}
