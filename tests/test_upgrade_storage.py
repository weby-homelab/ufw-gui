"""Existing installation data must survive the manual-recovery upgrade path."""

import os
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend import main
from backend.routers import auth_router, ufw_router
from backend.services import auth_service, database_service, filesystem_service


class UpgradeStorageTests(unittest.TestCase):
    def test_fresh_storage_allows_setup_then_login_without_a_replacement_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "stats.db"
            original_initialized = main.app.state.storage_initialized
            original_validated = main.app.state.storage_validated
            original_attempted = main.app.state.storage_initialization_attempted
            main.app.state.storage_initialized = False
            main.app.state.storage_validated = False
            main.app.state.storage_initialization_attempted = False
            try:
                with (
                    patch.dict(
                        os.environ,
                        {"UFW_GUI_SETUP_TOKEN": "fixture-setup-token-" + "x" * 32},
                    ),
                    patch.object(filesystem_service, "DATA_DIR", directory),
                    patch.object(
                        filesystem_service, "USER_DATA_FILE", str(root / "users.json")
                    ),
                    patch.object(
                        filesystem_service,
                        "TEST_STATE_FILE",
                        str(root / "test_state.json"),
                    ),
                    patch.object(database_service, "DATA_DIR", directory),
                    patch.object(database_service, "DB_FILE", str(database)),
                    patch.object(auth_router, "log_action"),
                ):
                    database_service.initialize_empty_database()
                    initial_inode = database.stat().st_ino
                    client = TestClient(
                        main.app,
                        base_url="https://testserver",
                        raise_server_exceptions=False,
                    )
                    self.assertEqual(client.get("/api/health").status_code, 200)
                    self.assertEqual(
                        client.get("/api/auth/setup-needed").json(),
                        {"setup_needed": True},
                    )
                    setup = client.post(
                        "/api/auth/setup",
                        json={
                            "username": "operator",
                            "password": "fixture-only-password",
                            "setup_token": "fixture-setup-token-" + "x" * 32,
                        },
                    )
                    self.assertEqual(setup.status_code, 200)
                    self.assertEqual(
                        client.get("/api/auth/setup-needed").json(),
                        {"setup_needed": False},
                    )
                    login = client.post(
                        "/api/auth/login",
                        data={
                            "username": "operator",
                            "password": "fixture-only-password",
                        },
                    )
                    self.assertEqual(login.status_code, 200)
                    headers = {
                        "Authorization": "Bearer " + login.json()["access_token"]
                    }
                    me = client.get("/api/auth/me", headers=headers)
                    self.assertEqual(me.status_code, 200)
                    self.assertEqual(
                        me.json(), {"username": "operator", "role": "superadmin"}
                    )
                    self.assertEqual(database.stat().st_ino, initial_inode)
            finally:
                main.app.state.storage_initialized = original_initialized
                main.app.state.storage_validated = original_validated
                main.app.state.storage_initialization_attempted = original_attempted

    def test_existing_database_with_wal_and_evidence_is_preserved(self):
        with tempfile.TemporaryDirectory() as parent:
            legacy = Path(parent) / "legacy"
            upgraded = Path(parent) / "upgraded"
            legacy.mkdir(mode=0o700)
            upgraded.mkdir(mode=0o700)
            legacy_db = legacy / "stats.db"

            with closing(sqlite3.connect(legacy_db)) as connection:
                self.assertEqual(
                    connection.execute("PRAGMA journal_mode=WAL").fetchone(), ("wal",)
                )
                connection.execute("PRAGMA wal_autocheckpoint=0")
                # This is the schema used by the previously shipped init_db().
                connection.executescript(
                    "CREATE TABLE drops (id INTEGER PRIMARY KEY, ts TIMESTAMP, "
                    "src TEXT, proto TEXT, port TEXT, UNIQUE(ts, src, port));"
                    "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, ts TIMESTAMP, "
                    "username TEXT, action TEXT, details TEXT);"
                    "CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, role TEXT);"
                )
                connection.execute(
                    "INSERT INTO users VALUES (?, ?, ?)",
                    (
                        "operator",
                        auth_service.hash_password("fixture-only-password"),
                        "superadmin",
                    ),
                )
                connection.execute(
                    "INSERT INTO audit_logs (username, action) VALUES (?, ?)",
                    ("operator", "existing-audit"),
                )
                connection.commit()

                # Take a stable fixture while this sole SQLite connection is idle;
                # schema and committed rows still reside in the uncheckpointed WAL.
                self.assertGreater((legacy / "stats.db-wal").stat().st_size, 0)
                for name in ("stats.db", "stats.db-wal", "stats.db-shm"):
                    shutil.copyfile(legacy / name, upgraded / name)

            marker = upgraded / "test_state.json"
            marker_bytes = b'{"status":"testing","legacy":true}\n'
            marker.write_bytes(marker_bytes)
            marker.chmod(0o600)
            backup = upgraded / "ufw_backups" / "test_rollback_config"
            backup.mkdir(parents=True)
            backup_file = backup / "ufw.conf"
            backup_bytes = b"existing firewall backup evidence\n"
            backup_file.write_bytes(backup_bytes)

            original_initialized = main.app.state.storage_initialized
            original_validated = main.app.state.storage_validated
            original_attempted = main.app.state.storage_initialization_attempted
            main.app.state.storage_initialized = False
            main.app.state.storage_validated = False
            main.app.state.storage_initialization_attempted = False
            try:
                with (
                    patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": ""}),
                    patch.object(filesystem_service, "DATA_DIR", str(upgraded)),
                    patch.object(
                        filesystem_service,
                        "USER_DATA_FILE",
                        str(upgraded / "users.json"),
                    ),
                    patch.object(filesystem_service, "TEST_STATE_FILE", str(marker)),
                    patch.object(database_service, "DATA_DIR", str(upgraded)),
                    patch.object(
                        database_service, "DB_FILE", str(upgraded / "stats.db")
                    ),
                    patch.object(
                        ufw_router, "run_ufw", new_callable=AsyncMock
                    ) as runner,
                ):
                    client = TestClient(main.app, raise_server_exceptions=False)
                    self.assertEqual(client.get("/api/health").status_code, 200)
                    login = client.post(
                        "/api/auth/login",
                        data={
                            "username": "operator",
                            "password": "fixture-only-password",
                        },
                    )
                    self.assertEqual(login.status_code, 200)
                    headers = {
                        "Authorization": "Bearer " + login.json()["access_token"]
                    }
                    status = client.get("/api/reload/status", headers=headers)
                    self.assertEqual(status.status_code, 200)
                    self.assertEqual(status.json()["mode"], "manual_recovery_required")
                    self.assertTrue(status.json()["firewall_mutations_blocked"])
                    for _ in range(2):
                        mutation = client.post(
                            "/api/toggle", json={"action": "disable"}, headers=headers
                        )
                        self.assertEqual(mutation.status_code, 503)
                    runner.assert_not_awaited()

                with closing(sqlite3.connect(upgraded / "stats.db")) as connection:
                    self.assertEqual(
                        connection.execute(
                            "SELECT username, role FROM users"
                        ).fetchall(),
                        [("operator", "superadmin")],
                    )
                    self.assertEqual(
                        connection.execute("SELECT action FROM audit_logs").fetchall(),
                        [("existing-audit",)],
                    )
                self.assertEqual(marker.read_bytes(), marker_bytes)
                self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
                self.assertEqual(backup_file.read_bytes(), backup_bytes)
            finally:
                main.app.state.storage_initialized = original_initialized
                main.app.state.storage_validated = original_validated
                main.app.state.storage_initialization_attempted = original_attempted


if __name__ == "__main__":
    unittest.main()
