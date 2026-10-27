"""Admin API fallbacks log safely and preserve intended HTTP failures."""

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.routers import admin_router
from backend.services import database_service, filesystem_service
from backend import main
from backend.services.auth_service import get_current_user


def create_test_database(directory):
    with closing(sqlite3.connect(os.path.join(directory, "stats.db"))) as database:
        database.executescript(
            "CREATE TABLE drops (id INTEGER PRIMARY KEY, ts TIMESTAMP, src TEXT, "
            "proto TEXT, port TEXT, UNIQUE(ts, src, port));"
            "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, ts TIMESTAMP, "
            "username TEXT, action TEXT, details TEXT);"
            "CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, role TEXT);"
        )
    with patch.object(database_service, "DB_FILE", os.path.join(directory, "stats.db")):
        database_service.init_db()


class AdminRouterErrorTests(unittest.IsolatedAsyncioTestCase):
    def test_audit_logs_require_a_superadmin_at_the_http_boundary(self):
        original_overrides = main.app.dependency_overrides.copy()
        original_validated = main.app.state.storage_validated
        original_initialized = main.app.state.storage_initialized
        main.app.state.storage_initialized = True
        main.app.state.storage_validated = True
        main.app.dependency_overrides.pop(get_current_user, None)
        try:
            with (
                patch.object(
                    main, "revalidate_persistent_storage", new_callable=AsyncMock
                ),
                patch.object(
                    admin_router, "get_audit_logs", return_value=[{"action": "fixture"}]
                ) as get_logs,
            ):
                client = TestClient(main.app)
                unauthenticated = client.get("/api/audit-logs")
                main.app.dependency_overrides[get_current_user] = lambda: {
                    "role": "admin",
                    "username": "operator",
                }
                regular = client.get("/api/audit-logs")
                main.app.dependency_overrides[get_current_user] = lambda: {
                    "role": "superadmin",
                    "username": "operator",
                }
                superadmin = client.get("/api/audit-logs")
            self.assertEqual(
                [
                    unauthenticated.status_code,
                    regular.status_code,
                    superadmin.status_code,
                ],
                [401, 403, 200],
            )
            self.assertEqual(superadmin.json(), {"logs": [{"action": "fixture"}]})
            get_logs.assert_called_once_with()
        finally:
            main.app.dependency_overrides.clear()
            main.app.dependency_overrides.update(original_overrides)
            main.app.state.storage_validated = original_validated
            main.app.state.storage_initialized = original_initialized

    def test_invalid_admin_created_passwords_never_reach_hash_or_storage(self):
        original_overrides = main.app.dependency_overrides.copy()
        original_validated = main.app.state.storage_validated
        original_initialized = main.app.state.storage_initialized
        main.app.state.storage_initialized = True
        main.app.state.storage_validated = True
        main.app.dependency_overrides[get_current_user] = lambda: {
            "role": "superadmin",
            "username": "operator",
        }
        try:
            with (
                patch.object(
                    main, "revalidate_persistent_storage", new_callable=AsyncMock
                ),
                patch.object(admin_router, "load_users", return_value={}),
                patch.object(admin_router, "hash_password") as hash_password,
                patch.object(admin_router, "create_regular_user") as create_user,
                patch.object(admin_router, "log_action") as audit,
            ):
                client = TestClient(main.app, raise_server_exceptions=False)
                responses = [
                    client.post(
                        "/api/users",
                        json={"username": "new-user", "password": password},
                    )
                    for password in ("", "short", "a" * 73, "🚀" * 20)
                ]
            self.assertTrue(
                all(response.status_code in (400, 422) for response in responses)
            )
            hash_password.assert_not_called()
            create_user.assert_not_called()
            audit.assert_not_called()
        finally:
            main.app.dependency_overrides.clear()
            main.app.dependency_overrides.update(original_overrides)
            main.app.state.storage_validated = original_validated
            main.app.state.storage_initialized = original_initialized

    def test_settings_validation_errors_do_not_echo_supplied_token(self):
        sentinel_value = "123456789:REAL_TOKEN_SENTINEL"
        original_overrides = main.app.dependency_overrides.copy()
        original_validation_state = main.app.state.storage_validated
        original_initialization_state = main.app.state.storage_initialized
        main.app.state.storage_validated = True
        main.app.state.storage_initialized = True
        main.app.dependency_overrides[get_current_user] = lambda: {
            "role": "superadmin",
            "username": "admin",
        }
        try:
            with patch.object(
                main, "revalidate_persistent_storage", new_callable=AsyncMock
            ):
                response = TestClient(main.app).post(
                    "/api/settings",
                    json={"tg_token": [sentinel_value], "tg_chat_id": "7"},
                )
        finally:
            main.app.dependency_overrides.clear()
            main.app.dependency_overrides.update(original_overrides)
            main.app.state.storage_validated = original_validation_state
            main.app.state.storage_initialized = original_initialization_state

        self.assertEqual(response.status_code, 422)
        self.assertNotIn(sentinel_value, response.text)

    def test_openapi_settings_schema_does_not_publish_token_example(self):
        schema = main.app.openapi()
        self.assertNotIn("123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ", repr(schema))

    async def test_settings_are_not_available_to_regular_admins(self):
        with self.assertRaises(HTTPException) as raised:
            await admin_router.get_settings(user={"role": "admin"})
        self.assertEqual(raised.exception.status_code, 403)

    async def test_superadmin_settings_never_return_telegram_token(self):
        sentinel_value = "telegram-token-private-sentinel"
        with patch.object(
            admin_router,
            "load_config",
            return_value={"tg_token": sentinel_value, "tg_chat_id": "private-chat-id"},
        ):
            settings = await admin_router.get_settings(user={"role": "superadmin"})

        self.assertNotIn("tg_token", settings)
        self.assertTrue(settings["tg_token_configured"])
        self.assertEqual(settings["tg_chat_id"], "private-chat-id")
        self.assertNotIn(sentinel_value, repr(settings))

    async def test_blank_settings_token_preserves_existing_secret(self):
        original = {"tg_token": "preserve-this-secret", "tg_chat_id": "old-chat"}
        with (
            patch.object(admin_router, "load_config", return_value=original.copy()),
            patch.object(admin_router, "save_config") as save,
        ):
            result = await admin_router.save_settings(
                data=admin_router.SettingsSchema(tg_token="", tg_chat_id="new-chat"),
                user={"role": "superadmin"},
            )

        self.assertEqual(result, {"status": "success"})
        save.assert_called_once_with(
            {"tg_token": "preserve-this-secret", "tg_chat_id": "new-chat"}
        )

    async def test_token_only_settings_update_preserves_existing_chat_id(self):
        original = {"tg_token": "old-token", "tg_chat_id": "existing-chat"}
        with (
            patch.object(admin_router, "load_config", return_value=original.copy()),
            patch.object(admin_router, "save_config") as save,
        ):
            await admin_router.save_settings(
                data=admin_router.SettingsSchema(tg_token="new-token"),
                user={"role": "superadmin"},
            )
        save.assert_called_once_with(
            {"tg_token": "new-token", "tg_chat_id": "existing-chat"}
        )

    async def test_audit_database_failure_has_safe_fallback_and_diagnostic(self):
        with (
            patch.object(
                admin_router,
                "get_audit_logs",
                side_effect=sqlite3.OperationalError("private audit sentinel"),
            ),
            self.assertLogs("backend.routers.admin_router", level="WARNING") as logs,
        ):
            self.assertEqual(
                await admin_router.get_audit(
                    user={"username": "admin", "role": "superadmin"}
                ),
                {"logs": []},
            )

        self.assertNotIn("private audit sentinel", "\n".join(logs.output))

    async def test_unexpected_settings_error_is_not_silently_converted_to_empty_data(
        self,
    ):
        with patch.object(
            admin_router, "load_config", side_effect=RuntimeError("bug sentinel")
        ):
            with self.assertRaisesRegex(RuntimeError, "bug sentinel"):
                await admin_router.get_settings(user={"role": "superadmin"})

    async def test_settings_write_failure_is_logged_without_error_details(self):
        with (
            patch.object(
                admin_router,
                "save_config",
                side_effect=PermissionError("private settings sentinel"),
            ),
            self.assertLogs("backend.routers.admin_router", level="ERROR") as logs,
        ):
            with self.assertRaises(HTTPException) as raised:
                await admin_router.save_settings(
                    data=admin_router.SettingsSchema(tg_token="fake", tg_chat_id="1"),
                    user={"role": "superadmin", "username": "admin"},
                )

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(raised.exception.detail, "Failed to save settings")
        self.assertNotIn("private settings sentinel", "\n".join(logs.output))

    async def test_snapshot_restore_is_disabled_for_superadmin_without_side_effects(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            with (
                patch.object(
                    filesystem_service,
                    "TEST_STATE_FILE",
                    os.path.join(directory, "test_state.json"),
                ),
                patch.object(
                    filesystem_service,
                    "restore_snapshot",
                    new_callable=AsyncMock,
                ) as restore,
                patch.object(admin_router, "log_action") as audit,
            ):
                with self.assertRaises(HTTPException) as raised:
                    await admin_router.restore_snapshot_route(
                        name="backup",
                        user={"username": "admin", "role": "superadmin"},
                    )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("snapshot_restore_unavailable", raised.exception.detail)
        restore.assert_not_awaited()
        audit.assert_not_called()

    async def test_snapshot_restore_requires_superadmin_role(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            with (
                patch.object(
                    filesystem_service,
                    "TEST_STATE_FILE",
                    os.path.join(directory, "test_state.json"),
                ),
                patch.object(
                    filesystem_service,
                    "restore_snapshot",
                    new_callable=AsyncMock,
                ) as restore,
            ):
                with self.assertRaises(HTTPException) as raised:
                    await admin_router.restore_snapshot_route(
                        name="backup", user={"username": "admin", "role": "admin"}
                    )

        self.assertEqual(raised.exception.status_code, 403)
        restore.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
