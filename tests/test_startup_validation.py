"""Persistent-storage validation cannot be bypassed by disabling ASGI lifespan."""

import asyncio
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import AsyncMock, patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import main
from backend.routers import ufw_router
from backend.services import auth_service, database_service, filesystem_service


class StartupValidationTests(unittest.TestCase):
    def setUp(self):
        self.original_validated = getattr(main.app.state, "storage_validated", False)
        self.original_initialized = getattr(
            main.app.state, "storage_initialized", False
        )
        self.original_attempted = main.app.state.storage_initialization_attempted
        main.app.state.storage_validated = False
        main.app.state.storage_initialized = False
        main.app.state.storage_initialization_attempted = False

    def tearDown(self):
        main.app.state.storage_validated = self.original_validated
        main.app.state.storage_initialized = self.original_initialized
        main.app.state.storage_initialization_attempted = self.original_attempted

    def test_first_http_request_validates_storage_without_lifespan_context(self):
        with (
            patch.object(main, "init_dirs") as init_dirs,
            patch.object(main, "init_db") as init_db,
            patch.object(
                main, "inspect_recovery_state_on_startup", new_callable=AsyncMock
            ) as inspect,
            patch.object(
                main, "revalidate_persistent_storage", new_callable=AsyncMock
            ) as revalidate,
        ):
            client = TestClient(main.app)
            first = client.get("/api/health")
            second = client.get("/api/health")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        init_dirs.assert_called_once_with()
        init_db.assert_called_once_with()
        inspect.assert_awaited_once_with()
        revalidate.assert_awaited_once_with()
        self.assertTrue(main.app.state.storage_validated)

    def test_invalid_storage_blocks_requests_when_lifespan_is_disabled(self):
        with (
            patch.object(main, "init_dirs", side_effect=RuntimeError("private path")),
            patch.object(main, "init_db") as init_db,
            patch.object(
                main, "inspect_recovery_state_on_startup", new_callable=AsyncMock
            ) as inspect,
        ):
            response = TestClient(main.app).get("/api/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"], "Persistent recovery storage is unavailable"
        )
        init_db.assert_not_called()
        inspect.assert_not_awaited()
        self.assertFalse(main.app.state.storage_validated)

    def test_lifespan_off_does_not_create_a_missing_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            with (
                patch.object(filesystem_service, "DATA_DIR", directory),
                patch.object(
                    filesystem_service,
                    "TEST_STATE_FILE",
                    os.path.join(directory, "test_state.json"),
                ),
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                response = TestClient(main.app).get("/api/health")

            self.assertEqual(response.status_code, 503)
            self.assertFalse(os.path.exists(database_path))
            self.assertFalse(main.app.state.storage_validated)

    def assert_failed_initial_storage_cannot_be_rebound(
        self, *, corrupt, missing_directory=False
    ):
        with tempfile.TemporaryDirectory() as parent:
            directory = os.path.join(parent, "active")
            replacement_directory = os.path.join(parent, "replacement")
            if not missing_directory:
                os.mkdir(directory, 0o700)
            os.mkdir(replacement_directory, 0o700)
            database_path = os.path.join(directory, "stats.db")
            replacement = os.path.join(replacement_directory, "stats.db")
            with patch.object(database_service, "DB_FILE", replacement):
                database_service.initialize_empty_database()
            with closing(sqlite3.connect(replacement)) as connection, connection:
                connection.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("operator", "test-password-hash", "admin"),
                )
            if corrupt:
                with open(database_path, "wb") as database:
                    database.write(b"corrupt initial database")

            with (
                patch.object(filesystem_service, "DATA_DIR", directory),
                patch.object(
                    filesystem_service,
                    "USER_DATA_FILE",
                    os.path.join(directory, "users.json"),
                ),
                patch.object(
                    filesystem_service,
                    "TEST_STATE_FILE",
                    os.path.join(directory, "test_state.json"),
                ),
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
                patch.object(ufw_router, "run_ufw", new_callable=AsyncMock) as runner,
                patch.object(ufw_router, "log_action"),
            ):
                runner.return_value = "mocked"
                client = TestClient(main.app, raise_server_exceptions=False)
                self.assertEqual(client.get("/api/health").status_code, 503)
                if missing_directory:
                    os.mkdir(directory, 0o700)
                if corrupt:
                    os.replace(database_path, os.path.join(parent, "corrupt-evidence"))
                os.replace(replacement, database_path)
                token = auth_service.create_access_token("operator", "admin")
                responses = [
                    client.get("/api/health"),
                    client.get("/api/auth/setup-needed"),
                    client.post(
                        "/api/toggle",
                        json={"action": "disable"},
                        headers={"Authorization": f"Bearer {token}"},
                    ),
                ]
                self.assertEqual(
                    [response.status_code for response in responses], [503, 503, 503]
                )
                for response in responses:
                    self.assertEqual(
                        response.json(),
                        {"detail": "Persistent recovery storage is unavailable"},
                    )
                runner.assert_not_awaited()

    def test_missing_initial_database_cannot_be_rebound_without_restart(self):
        self.assert_failed_initial_storage_cannot_be_rebound(corrupt=False)

    def test_corrupt_initial_database_cannot_be_rebound_without_restart(self):
        self.assert_failed_initial_storage_cannot_be_rebound(corrupt=True)

    def test_missing_initial_directory_cannot_be_rebound_without_restart(self):
        self.assert_failed_initial_storage_cannot_be_rebound(
            corrupt=False, missing_directory=True
        )

    def test_lifespan_off_accepts_explicitly_initialized_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            with (
                patch.object(filesystem_service, "DATA_DIR", directory),
                patch.object(
                    filesystem_service,
                    "TEST_STATE_FILE",
                    os.path.join(directory, "test_state.json"),
                ),
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                database_service.initialize_empty_database()
                with closing(sqlite3.connect(database_path)) as connection, connection:
                    connection.execute(
                        "INSERT INTO audit_logs (username, action) VALUES ('u', 'a')"
                    )
                response = TestClient(main.app).get("/api/health")

            self.assertEqual(response.status_code, 200)
            self.assertTrue(main.app.state.storage_validated)

    def test_http_endpoints_fail_closed_after_database_disappears(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            marker_path = os.path.join(directory, "test_state.json")
            with (
                patch.object(filesystem_service, "DATA_DIR", directory),
                patch.object(filesystem_service, "TEST_STATE_FILE", marker_path),
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                database_service.initialize_empty_database()
                with closing(sqlite3.connect(database_path)) as connection, connection:
                    connection.execute(
                        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                        ("operator", "test-password-hash", "admin"),
                    )

                token = auth_service.create_access_token("operator", "admin")
                client = TestClient(main.app, raise_server_exceptions=False)
                self.assertEqual(client.get("/api/health").status_code, 200)
                os.unlink(database_path)

                with patch.object(
                    ufw_router, "run_ufw", new_callable=AsyncMock
                ) as firewall_runner:
                    responses = [
                        client.get("/api/health"),
                        client.get("/api/auth/setup-needed"),
                        client.post(
                            "/api/toggle",
                            json={"action": "disable"},
                            headers={"Authorization": f"Bearer {token}"},
                        ),
                    ]

                self.assertEqual(
                    [response.status_code for response in responses],
                    [
                        503,
                        503,
                        503,
                    ],
                )
                for response in responses:
                    self.assertEqual(
                        response.json(),
                        {"detail": "Persistent recovery storage is unavailable"},
                    )
                firewall_runner.assert_not_awaited()
                self.assertFalse(os.path.exists(database_path))

    def test_storage_health_is_distinct_from_firewall_mutation_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            marker_path = os.path.join(directory, "test_state.json")
            marker_bytes = b'{"status":"testing"}\n'
            with (
                patch.object(filesystem_service, "DATA_DIR", directory),
                patch.object(filesystem_service, "TEST_STATE_FILE", marker_path),
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                database_service.initialize_empty_database()
                with closing(sqlite3.connect(database_path)) as connection, connection:
                    connection.execute(
                        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                        ("operator", "test-password-hash", "admin"),
                    )
                with open(marker_path, "wb") as marker:
                    marker.write(marker_bytes)

                token = auth_service.create_access_token("operator", "admin")
                client = TestClient(main.app, raise_server_exceptions=False)
                health = client.get("/api/health")
                recovery = client.get(
                    "/api/reload/status",
                    headers={"Authorization": f"Bearer {token}"},
                )

                self.assertEqual(health.status_code, 200)
                self.assertEqual(recovery.status_code, 200)
                self.assertEqual(recovery.json()["mode"], "manual_recovery_required")
                self.assertTrue(recovery.json()["firewall_mutations_blocked"])
                with open(marker_path, "rb") as marker:
                    self.assertEqual(marker.read(), marker_bytes)

    def test_http_health_fails_closed_after_same_inode_database_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            marker_path = os.path.join(directory, "test_state.json")
            with (
                patch.object(filesystem_service, "DATA_DIR", directory),
                patch.object(filesystem_service, "TEST_STATE_FILE", marker_path),
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                database_service.initialize_empty_database()
                client = TestClient(main.app, raise_server_exceptions=False)
                self.assertEqual(client.get("/api/health").status_code, 200)
                original_inode = os.stat(database_path).st_ino

                with open(database_path, "r+b") as database:
                    database.seek(0)
                    database.write(b"\x00" * 64)
                    database.flush()
                    os.fsync(database.fileno())
                    database.seek(0)
                    corrupted_header = database.read(64)

                response = client.get("/api/health")

                self.assertEqual(response.status_code, 503)
                self.assertEqual(
                    response.json(),
                    {"detail": "Persistent recovery storage is unavailable"},
                )
                self.assertEqual(os.stat(database_path).st_ino, original_inode)
                with open(database_path, "rb") as database:
                    self.assertEqual(database.read(64), corrupted_header)


class StartupValidationConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    def create_app(self):
        app = FastAPI()
        app.state.storage_validation_lock = asyncio.Lock()
        app.state.storage_initialized = False
        app.state.storage_initialization_attempted = False
        app.state.storage_validated = False
        return app

    async def test_concurrent_initial_requests_bind_storage_only_once(self):
        app = self.create_app()
        inspection_started = asyncio.Event()
        continue_inspection = asyncio.Event()

        async def wait_for_inspection():
            inspection_started.set()
            await continue_inspection.wait()

        with (
            patch.object(main, "init_dirs") as init_dirs,
            patch.object(main, "init_db") as init_db,
            patch.object(
                main,
                "inspect_recovery_state_on_startup",
                side_effect=wait_for_inspection,
            ),
            patch.object(
                main, "revalidate_persistent_storage", new_callable=AsyncMock
            ) as revalidate,
        ):
            first = asyncio.create_task(main.ensure_persistent_storage_validated(app))
            await asyncio.wait_for(inspection_started.wait(), timeout=1)
            second = asyncio.create_task(main.ensure_persistent_storage_validated(app))
            await asyncio.sleep(0)
            self.assertFalse(second.done())
            continue_inspection.set()
            await asyncio.wait_for(asyncio.gather(first, second), timeout=1)

        init_dirs.assert_called_once_with()
        init_db.assert_called_once_with()
        revalidate.assert_awaited_once_with()
        self.assertTrue(app.state.storage_validated)

    async def test_cancelled_startup_inspection_revalidates_without_rebinding(self):
        app = self.create_app()
        inspection_started = asyncio.Event()

        async def wait_for_cancellation():
            inspection_started.set()
            await asyncio.Event().wait()

        with (
            patch.object(main, "init_dirs") as init_dirs,
            patch.object(main, "init_db") as init_db,
            patch.object(
                main,
                "inspect_recovery_state_on_startup",
                side_effect=wait_for_cancellation,
            ),
            patch.object(
                main, "revalidate_persistent_storage", new_callable=AsyncMock
            ) as revalidate,
        ):
            first = asyncio.create_task(main.ensure_persistent_storage_validated(app))
            await asyncio.wait_for(inspection_started.wait(), timeout=1)
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first
            self.assertFalse(app.state.storage_validated)
            await main.ensure_persistent_storage_validated(app)

        init_dirs.assert_called_once_with()
        init_db.assert_called_once_with()
        revalidate.assert_awaited_once_with()
        self.assertTrue(app.state.storage_validated)


if __name__ == "__main__":
    unittest.main()
