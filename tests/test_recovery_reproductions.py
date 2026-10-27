"""Known failing reproductions for draft review, not proof of safe recovery.

Scheduling a task or keeping it pending is necessary but not sufficient for
crash-safe or cross-process recovery. All firewall operations are mocked.
"""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")
from backend.routers import reload_router
from backend.services import filesystem_service


class RecoveryReproductions(unittest.IsolatedAsyncioTestCase):
    async def test_reload_error_must_not_leave_marker_without_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = os.path.join(directory, "test_state.json")
            with (
                patch.object(filesystem_service, "DATA_DIR", directory),
                patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                patch.object(reload_router, "UFW_BACKUP_DIR", directory),
                patch.object(reload_router.os.path, "ismount", return_value=False),
                patch.object(
                    reload_router, "save_test_rollback", new_callable=AsyncMock
                ),
                patch.object(
                    reload_router,
                    "run_ufw",
                    new_callable=AsyncMock,
                    side_effect=RuntimeError("injected reload failure"),
                ),
                patch.object(reload_router, "rollback_task_ref", None),
            ):
                with self.assertRaisesRegex(RuntimeError, "injected reload failure"):
                    await reload_router.reload_test(user={"username": "test"})
                self.assertEqual(
                    filesystem_service.get_test_state()["status"], "testing"
                )
                self.assertIsNotNone(
                    reload_router.rollback_task_ref,
                    "persistent marker has no scheduled recovery",
                )

    async def test_confirm_error_must_not_cancel_pending_recovery(self):
        pending = asyncio.create_task(asyncio.Event().wait())
        try:
            with tempfile.TemporaryDirectory() as directory:
                marker = os.path.join(directory, "test_state.json")
                with (
                    patch.object(filesystem_service, "DATA_DIR", directory),
                    patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                    patch.object(reload_router, "rollback_task_ref", pending),
                    patch.object(
                        reload_router,
                        "clear_test_state",
                        side_effect=PermissionError("injected"),
                    ),
                ):
                    filesystem_service.save_test_state({"status": "testing"})
                    with self.assertRaisesRegex(PermissionError, "injected"):
                        await reload_router.reload_confirm(user={"username": "test"})
                    self.assertEqual(
                        filesystem_service.get_test_state()["status"], "testing"
                    )
                    await asyncio.sleep(0)
                    self.assertFalse(
                        pending.done(), "marker remains but recovery was cancelled"
                    )
        finally:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
