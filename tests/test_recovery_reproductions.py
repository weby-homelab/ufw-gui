"""R1/R2 regressions for the explicit fail-closed recovery contract B.

The pre-mitigation RED evidence is recorded in the execution report. These
tests prove refusal and evidence preservation only; they are not proof of
successful recovery or real firewall behavior.
"""

import asyncio
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

from fastapi import HTTPException

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.routers import reload_router
from backend.services import (
    database_service,
    filesystem_service,
    recovery_guard,
    subprocess_service,
)


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


class RecoveryReproductions(unittest.IsolatedAsyncioTestCase):
    async def test_wal_schema_change_after_admission_blocks_subprocess(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "test_state.json")
            database_path = os.path.join(directory, "stats.db")
            database = sqlite3.connect(database_path)
            self.assertEqual(
                database.execute("PRAGMA journal_mode=WAL").fetchone(), ("wal",)
            )
            database.execute("PRAGMA wal_autocheckpoint=0")

            try:
                with (
                    patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                    patch.object(subprocess_service, "run") as firewall_runner,
                ):
                    async with recovery_guard.firewall_mutation_guard():
                        descriptors = recovery_guard.mutation_lock_descriptors()
                        self.assertIsNotNone(descriptors)
                        assert descriptors is not None

                        database.execute(
                            "CREATE TRIGGER forbidden_trigger AFTER INSERT ON users "
                            "BEGIN SELECT 1; END"
                        )
                        database.commit()
                        self.assertTrue(os.path.exists(f"{database_path}-wal"))
                        self.assertFalse(
                            filesystem_service._application_database_is_valid(
                                directory_fd=descriptors[0],
                                database_fd=descriptors[1],
                            )
                        )

                        with self.assertRaises(HTTPException) as raised:
                            subprocess_service._run_with_final_recovery_check(
                                ["ufw", "status"], descriptors
                            )

                        self.assertEqual(raised.exception.status_code, 503)

                    firewall_runner.assert_not_called()
            finally:
                database.close()

    async def test_same_inode_database_corruption_after_admission_blocks_subprocess(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "test_state.json")
            database_path = os.path.join(directory, "stats.db")

            with (
                patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                patch.object(subprocess_service, "run") as firewall_runner,
            ):
                async with recovery_guard.firewall_mutation_guard():
                    descriptors = recovery_guard.mutation_lock_descriptors()
                    self.assertIsNotNone(descriptors)
                    assert descriptors is not None

                    with open(database_path, "r+b") as database:
                        database.seek(0)
                        database.write(b"\x00" * 64)
                        database.flush()
                        os.fsync(database.fileno())

                    self.assertFalse(
                        filesystem_service._application_database_is_valid(
                            directory_fd=descriptors[0],
                            database_fd=descriptors[1],
                        )
                    )
                    with self.assertRaises(HTTPException) as raised:
                        subprocess_service._run_with_final_recovery_check(
                            ["ufw", "status"], descriptors
                        )

                    self.assertEqual(raised.exception.status_code, 503)

                firewall_runner.assert_not_called()

    async def test_r1_repeated_test_requests_refuse_before_marker_or_backup_changes(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "test_state.json")
            backup_dir = os.path.join(directory, "ufw_backups")
            os.mkdir(backup_dir)
            backup = os.path.join(backup_dir, "test_rollback_config")
            backup_bytes = b"legacy rollback backup evidence must be preserved\n"
            with open(backup, "wb") as evidence:
                evidence.write(backup_bytes)

            with patch.object(filesystem_service, "TEST_STATE_FILE", marker):
                for _ in range(2):
                    with self.assertRaises(reload_router.HTTPException) as raised:
                        await reload_router.reload_test(user={"username": "test"})
                    self.assertEqual(raised.exception.status_code, 503)
                    self.assertIn("test_mode_unavailable", raised.exception.detail)
                    self.assertFalse(os.path.lexists(marker))
                    self.assertEqual(os.listdir(backup_dir), ["test_rollback_config"])
                    with open(backup, "rb") as evidence:
                        self.assertEqual(evidence.read(), backup_bytes)

    async def test_r2_confirm_preserves_marker_without_scheduling_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "test_state.json")
            marker_bytes = b'{"status":"testing","legacy":true}\n'
            with open(marker, "wb") as evidence:
                evidence.write(marker_bytes)
            os.chmod(marker, 0o600)

            with (
                patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                patch.object(asyncio, "create_task") as create_task,
            ):
                with self.assertRaises(reload_router.HTTPException) as raised:
                    await reload_router.reload_confirm(user={"username": "test"})
                self.assertEqual(raised.exception.status_code, 503)
                self.assertIn("manual_recovery_required", raised.exception.detail)
                create_task.assert_not_called()

            with open(marker, "rb") as evidence:
                self.assertEqual(evidence.read(), marker_bytes)
            self.assertEqual(os.stat(marker).st_mode & 0o777, 0o600)
