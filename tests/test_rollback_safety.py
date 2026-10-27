"""Legacy rollback paths now fail closed under recovery contract B.

These checks intentionally prove only no-side-effects and evidence retention.
They are not integration tests of UFW or successful automatic recovery.
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

from backend import main
from backend.routers import admin_router, reload_router
from backend.services import database_service, filesystem_service, subprocess_service


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


class RollbackSafetyTests(unittest.TestCase):
    def test_startup_missing_backup_retains_legacy_state_without_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            original = b'{"status":"testing","backup":"missing"}\n'
            with open(marker, "wb") as output:
                output.write(original)
            with patch.object(filesystem_service, "TEST_STATE_FILE", marker):
                asyncio.run(main.inspect_recovery_state_on_startup())
            with open(marker, "rb") as output:
                self.assertEqual(output.read(), original)

    def test_startup_bind_mount_state_is_not_inspected_or_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            with open(marker, "wb") as output:
                output.write(b"legacy marker")
            with (
                patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                patch.object(main.os.path, "ismount", return_value=True) as ismount,
            ):
                asyncio.run(main.inspect_recovery_state_on_startup())
            ismount.assert_not_called()
            with open(marker, "rb") as output:
                self.assertEqual(output.read(), b"legacy marker")

    def test_startup_does_not_invoke_reload_even_when_it_would_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            with open(marker, "wb") as output:
                output.write(b"state preserved")
            with patch.object(filesystem_service, "TEST_STATE_FILE", marker):
                asyncio.run(main.inspect_recovery_state_on_startup())
            with open(marker, "rb") as output:
                self.assertEqual(output.read(), b"state preserved")

    def test_startup_never_clears_a_legacy_marker_after_recovery(self):
        self.test_startup_missing_backup_retains_legacy_state_without_recovery()

    def test_timer_bind_mount_path_is_inert_and_preserves_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            original = b"legacy timer marker"
            with open(marker, "wb") as output:
                output.write(original)
            with patch.object(filesystem_service, "TEST_STATE_FILE", marker):
                asyncio.run(reload_router.perform_rollback())
            with open(marker, "rb") as output:
                self.assertEqual(output.read(), original)

    def test_test_mode_refuses_before_any_marker_or_firewall_change(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            with (
                patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                patch.object(subprocess_service, "run") as run,
            ):
                with self.assertRaises(reload_router.HTTPException) as raised:
                    asyncio.run(reload_router.reload_test(user={"username": "admin"}))
            self.assertEqual(raised.exception.status_code, 503)
            self.assertIn("test_mode_unavailable", raised.exception.detail)
            run.assert_not_called()
            self.assertFalse(os.path.lexists(marker))




class RecoveryMarkerTests(unittest.TestCase):
    def test_missing_marker_is_the_only_unresolved_false_case(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            with patch.object(filesystem_service, "TEST_STATE_FILE", marker):
                self.assertFalse(filesystem_service.has_unresolved_test_marker())
                with open(marker, "wb") as output:
                    output.write(b"corrupt marker")
                self.assertTrue(filesystem_service.has_unresolved_test_marker())

    def test_empty_replacement_directory_is_not_a_valid_recovery_store(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = os.path.join(directory, "state.json")
            database = os.path.join(directory, "stats.db")
            open(database, "wb").close()
            with patch.object(filesystem_service, "TEST_STATE_FILE", marker):
                self.assertTrue(filesystem_service.has_unresolved_test_marker())

    def test_missing_marker_parent_is_uninspectable_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = os.path.join(directory, "missing", "state.json")
            with patch.object(filesystem_service, "TEST_STATE_FILE", marker):
                self.assertTrue(filesystem_service.has_unresolved_test_marker())
            self.assertFalse(os.path.exists(os.path.dirname(marker)))

    def test_init_dirs_does_not_recreate_missing_persistent_data_directory(self):
        with tempfile.TemporaryDirectory() as parent:
            missing_directory = os.path.join(parent, "missing-data")
            with (
                patch.object(filesystem_service, "DATA_DIR", missing_directory),
                patch.object(
                    filesystem_service,
                    "UFW_BACKUP_DIR",
                    os.path.join(missing_directory, "ufw_backups"),
                ),
            ):
                with self.assertRaises(RuntimeError):
                    filesystem_service.init_dirs()
            self.assertFalse(os.path.exists(missing_directory))

    def test_corrupt_marker_bytes_and_permissions_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            original = b"{not valid JSON\xff\n"
            with open(marker, "wb") as output:
                output.write(original)
            os.chmod(marker, 0o640)
            with patch.object(filesystem_service, "TEST_STATE_FILE", marker):
                self.assertTrue(filesystem_service.has_unresolved_test_marker())
            with open(marker, "rb") as output:
                self.assertEqual(output.read(), original)
            self.assertEqual(os.stat(marker).st_mode & 0o777, 0o640)

    def test_marker_inspection_error_is_not_treated_as_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            original_lstat = filesystem_service.os.lstat

            def fail_marker_inspection(path):
                if path == marker:
                    raise PermissionError("denied")
                return original_lstat(path)

            with (
                patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                patch.object(
                    filesystem_service.os, "lstat", side_effect=fail_marker_inspection
                ),
            ):
                self.assertTrue(filesystem_service.has_unresolved_test_marker())

    def test_dangling_symlink_is_an_unresolved_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            os.symlink(os.path.join(directory, "missing"), marker)
            with patch.object(filesystem_service, "TEST_STATE_FILE", marker):
                self.assertTrue(filesystem_service.has_unresolved_test_marker())
            self.assertTrue(os.path.islink(marker))

    def test_markered_snapshot_restore_refuses_before_target_or_mount_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            snapshot = os.path.join(directory, "snapshot")
            os.mkdir(snapshot)
            with open(marker, "wb") as output:
                output.write(b"unresolved")
            with (
                patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                patch.object(filesystem_service, "UFW_BACKUP_DIR", directory),
            ):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(filesystem_service.restore_snapshot("snapshot"))
            self.assertEqual(raised.exception.status_code, 503)
            with open(marker, "rb") as output:
                self.assertEqual(output.read(), b"unresolved")

    def test_reserved_legacy_rollback_backup_is_preserved_when_restore_is_disabled(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            backup = os.path.join(directory, "test_rollback_config")
            os.mkdir(backup)
            with open(
                os.path.join(backup, "ufw.conf"), "w", encoding="utf-8"
            ) as output:
                output.write("legacy backup evidence")
            with (
                patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                patch.object(filesystem_service, "UFW_BACKUP_DIR", directory),
            ):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(
                        filesystem_service.restore_snapshot("test_rollback_config")
                    )
            self.assertEqual(raised.exception.status_code, 503)
            self.assertIn("snapshot_restore_unavailable", raised.exception.detail)
            with open(os.path.join(backup, "ufw.conf"), encoding="utf-8") as output:
                self.assertEqual(output.read(), "legacy backup evidence")

    def test_snapshot_restore_refuses_symlink_alias_to_reserved_legacy_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "state.json")
            backup_dir = os.path.join(directory, "ufw_backups")
            os.mkdir(backup_dir)
            legacy = os.path.join(backup_dir, "test_rollback_config")
            os.mkdir(legacy)
            evidence = os.path.join(legacy, "ufw.conf")
            with open(evidence, "wb") as output:
                output.write(b"preserve legacy rollback evidence")
            alias = os.path.join(backup_dir, "manual-review-alias")
            os.symlink(legacy, alias)

            with (
                patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                patch.object(filesystem_service, "UFW_BACKUP_DIR", backup_dir),
            ):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(
                        admin_router.restore_snapshot_route(
                            name="manual-review-alias",
                            user={"username": "admin", "role": "superadmin"},
                        )
                    )

            self.assertEqual(raised.exception.status_code, 503)
            self.assertIn("snapshot_restore_unavailable", raised.exception.detail)
            self.assertTrue(os.path.islink(alias))
            with open(evidence, "rb") as output:
                self.assertEqual(output.read(), b"preserve legacy rollback evidence")

    def test_new_snapshot_creation_is_disabled_without_reading_firewall_files(self):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(filesystem_service.create_snapshot("before_rule_change"))

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("snapshot_creation_unavailable", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
