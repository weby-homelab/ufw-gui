"""Recovery-status endpoints; automatic test/rollback mode is disabled."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.services.auth_service import get_current_user
from backend.services.recovery_guard import (
    MANUAL_RECOVERY_REQUIRED,
    has_unresolved_recovery_marker,
    protect_firewall_mutation,
    recovery_state_lock,
)

current_user_dependency = Depends(get_current_user)

router = APIRouter(prefix="/api/reload", tags=["Recovery"])

TEST_MODE_UNAVAILABLE = (
    "test_mode_unavailable: automatic rollback is disabled; firewall changes "
    "apply immediately and must be verified by the operator."
)


@router.get("/status")
async def get_recovery_status(user=current_user_dependency):
    async with recovery_state_lock():
        unresolved = has_unresolved_recovery_marker()
    return {
        "mode": "manual_recovery_required" if unresolved else "immediate_apply",
        "unresolved_marker": unresolved,
        "automatic_rollback": False,
        "firewall_mutations_blocked": unresolved,
        "detail": MANUAL_RECOVERY_REQUIRED if unresolved else TEST_MODE_UNAVAILABLE,
    }


async def perform_rollback():
    """Legacy task entrypoint retained as a side-effect-free fail-closed stub."""
    logging.getLogger(__name__).error(
        "Automatic firewall rollback is disabled; no files or firewall state were changed."
    )


@router.post("/test")
@protect_firewall_mutation
async def reload_test(user=current_user_dependency):
    raise HTTPException(status_code=503, detail=TEST_MODE_UNAVAILABLE)


@router.post("/confirm")
@protect_firewall_mutation
async def reload_confirm(user=current_user_dependency):
    raise HTTPException(status_code=503, detail=TEST_MODE_UNAVAILABLE)
