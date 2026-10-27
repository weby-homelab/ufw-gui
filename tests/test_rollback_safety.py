"""Rollback must preserve evidence and must not delete a host bind mount."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")
from backend import main
from backend.routers import reload_router


class RollbackSafetyTests(unittest.TestCase):
    def test_startup_missing_backup_retains_state(self):
        with patch.object(main, "get_test_state", return_value={"status": "testing"}), \
             patch.object(main, "get_test_rollback_path", return_value="/missing-backup"), \
             patch.object(main.os.path, "isdir", return_value=False), \
             patch.object(main, "clear_test_state") as clear, \
             patch.object(main.asyncio, "to_thread", new_callable=AsyncMock) as operation:
            asyncio.run(main.check_and_rollback_on_startup())
            clear.assert_not_called()
            operation.assert_not_called()

    def test_startup_bind_mount_is_not_removed_or_marked_successful(self):
        with patch.object(main, "get_test_state", return_value={"status": "testing"}), \
             patch.object(main, "get_test_rollback_path", return_value="/backup"), \
             patch.object(main.os.path, "isdir", return_value=True), \
             patch.object(main.os.path, "ismount", return_value=True), \
             patch.object(main, "clear_test_state") as clear, \
             patch.object(main.asyncio, "to_thread", new_callable=AsyncMock) as operation:
            asyncio.run(main.check_and_rollback_on_startup())
            clear.assert_not_called()
            operation.assert_not_called()

    def test_startup_reload_failure_retains_state(self):
        with patch.object(main, "get_test_state", return_value={"status": "testing"}), \
             patch.object(main, "get_test_rollback_path", return_value="/backup"), \
             patch.object(main.os.path, "isdir", return_value=True), \
             patch.object(main.os.path, "ismount", return_value=False), \
             patch.object(main.os.path, "exists", return_value=False), \
             patch.object(main, "clear_test_state") as clear, \
             patch.object(main.asyncio, "to_thread", new_callable=AsyncMock), \
             patch.object(main, "run_ufw", new_callable=AsyncMock, side_effect=RuntimeError("reload failed")):
            asyncio.run(main.check_and_rollback_on_startup())
            clear.assert_not_called()

    def test_startup_success_clears_state(self):
        with patch.object(main, "get_test_state", return_value={"status": "testing"}), \
             patch.object(main, "get_test_rollback_path", return_value="/backup"), \
             patch.object(main.os.path, "isdir", return_value=True), \
             patch.object(main.os.path, "ismount", return_value=False), \
             patch.object(main.os.path, "exists", return_value=False), \
             patch.object(main, "clear_test_state") as clear, \
             patch.object(main, "log_action"), \
             patch.object(main.asyncio, "to_thread", new_callable=AsyncMock), \
             patch.object(main, "run_ufw", new_callable=AsyncMock):
            asyncio.run(main.check_and_rollback_on_startup())
            clear.assert_called_once()

    def test_timer_bind_mount_is_not_removed_or_marked_successful(self):
        with patch.object(reload_router, "get_test_state", return_value={"status": "testing"}), \
             patch.object(reload_router, "get_test_rollback_path", return_value="/backup"), \
             patch.object(reload_router.os.path, "isdir", return_value=True), \
             patch.object(reload_router.os.path, "ismount", return_value=True), \
             patch.object(reload_router, "clear_test_state") as clear, \
             patch.object(reload_router.asyncio, "sleep", new_callable=AsyncMock), \
             patch.object(reload_router.asyncio, "to_thread", new_callable=AsyncMock) as operation:
            asyncio.run(reload_router.perform_rollback())
            clear.assert_not_called()
            operation.assert_not_called()



    def test_test_mode_refuses_mounted_firewall_before_any_changes(self):
        with patch.object(reload_router.os.path, "ismount", return_value=True), \
             patch.object(reload_router, "save_test_rollback", new_callable=AsyncMock) as backup, \
             patch.object(reload_router, "save_test_state") as save, \
             patch.object(reload_router, "run_ufw", new_callable=AsyncMock) as run:
            with self.assertRaises(reload_router.HTTPException) as raised:
                asyncio.run(reload_router.reload_test(user={"username": "admin"}))
            self.assertEqual(raised.exception.status_code, 503)
            self.assertIn("rollback", raised.exception.detail)
            backup.assert_not_called()
            save.assert_not_called()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
