"""Fail-closed contracts for disabled automatic recovery mode B."""

import asyncio
import contextvars
import fcntl
import os
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import AsyncMock, patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend import main
from backend.routers import admin_router, fail2ban_router, reload_router, ufw_router
from backend.services import database_service, filesystem_service, recovery_guard
from backend.services import subprocess_service


class ManualRecoveryModeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.marker = os.path.join(self.directory.name, "test_state.json")
        self.marker_patch = patch.object(
            filesystem_service, "TEST_STATE_FILE", self.marker
        )
        self.marker_patch.start()
        with closing(
            sqlite3.connect(os.path.join(self.directory.name, "stats.db"))
        ) as db:
            db.executescript(
                "CREATE TABLE drops (id INTEGER PRIMARY KEY, ts TIMESTAMP, src TEXT, "
                "proto TEXT, port TEXT, UNIQUE(ts, src, port));"
                "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, ts TIMESTAMP, "
                "username TEXT, action TEXT, details TEXT);"
                "CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, role TEXT);"
            )
        with patch.object(
            database_service,
            "DB_FILE",
            os.path.join(self.directory.name, "stats.db"),
        ):
            database_service.init_db()
        self.marker_bytes = b"legacy recovery evidence: do not parse or overwrite\n"
        with open(self.marker, "wb") as marker:
            marker.write(self.marker_bytes)
        os.chmod(self.marker, 0o640)

    async def asyncTearDown(self):
        self.marker_patch.stop()
        self.directory.cleanup()

    def assert_marker_unchanged(self):
        with open(self.marker, "rb") as marker:
            self.assertEqual(marker.read(), self.marker_bytes)
        self.assertEqual(os.stat(self.marker).st_mode & 0o777, 0o640)

    async def test_test_and_confirm_refuse_without_changing_legacy_evidence(self):
        for endpoint in (reload_router.reload_test, reload_router.reload_confirm):
            with self.subTest(endpoint=endpoint.__name__):
                with self.assertRaises(reload_router.HTTPException) as raised:
                    await endpoint(user={"username": "admin"})
                self.assertEqual(raised.exception.status_code, 503)
                self.assertIn("manual_recovery_required", raised.exception.detail)
                self.assert_marker_unchanged()

    async def test_test_mode_is_unavailable_even_without_a_marker(self):
        os.remove(self.marker)
        with self.assertRaises(reload_router.HTTPException) as raised:
            await reload_router.reload_test(user={"username": "admin"})
        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("test_mode_unavailable", raised.exception.detail)
        self.assertFalse(os.path.lexists(self.marker))

    async def test_rollback_entrypoint_is_inert_and_preserves_marker(self):
        await reload_router.perform_rollback()
        self.assert_marker_unchanged()

    async def test_startup_does_not_parse_or_restore_any_existing_marker(self):
        await main.inspect_recovery_state_on_startup()
        await main.inspect_recovery_state_on_startup()
        self.assert_marker_unchanged()

    async def test_startup_preserves_corrupt_marker_without_parsing_it(self):
        corrupt = b"\xffnot-json\x00\n"
        with open(self.marker, "wb") as marker:
            marker.write(corrupt)
        os.chmod(self.marker, 0o600)

        await main.inspect_recovery_state_on_startup()

        with open(self.marker, "rb") as marker:
            self.assertEqual(marker.read(), corrupt)
        self.assertEqual(os.stat(self.marker).st_mode & 0o777, 0o600)

    async def test_status_reports_unresolved_marker_without_following_it(self):
        status = await reload_router.get_recovery_status(user={"username": "admin"})
        self.assertEqual(status["mode"], "manual_recovery_required")
        self.assertTrue(status["unresolved_marker"])
        self.assertFalse(status["automatic_rollback"])
        self.assertTrue(status["firewall_mutations_blocked"])

        os.remove(self.marker)
        os.symlink(os.path.join(self.directory.name, "missing-target"), self.marker)
        status = await reload_router.get_recovery_status(user={"username": "admin"})
        self.assertTrue(status["unresolved_marker"])
        self.assertTrue(os.path.islink(self.marker))
        with self.assertRaises(ufw_router.HTTPException) as raised:
            await ufw_router.toggle_ufw(action="disable", user={"username": "admin"})
        self.assertEqual(raised.exception.status_code, 503)
        self.assertTrue(os.path.islink(self.marker))

    async def test_marker_inspection_error_fails_closed(self):
        with patch.object(
            filesystem_service.os,
            "lstat",
            side_effect=PermissionError("inspection denied"),
        ):
            self.assertTrue(filesystem_service.has_unresolved_test_marker())
            with self.assertRaises(ufw_router.HTTPException) as raised:
                await ufw_router.toggle_ufw(
                    action="disable", user={"username": "admin"}
                )
        self.assertEqual(raised.exception.status_code, 503)

    async def test_missing_recovery_directory_does_not_get_created_for_mutation(self):
        with tempfile.TemporaryDirectory() as parent:
            missing_directory = os.path.join(parent, "missing-data")
            marker_path = os.path.join(missing_directory, "test_state.json")
            with (
                patch.object(filesystem_service, "TEST_STATE_FILE", marker_path),
                patch.object(ufw_router, "run_ufw", new_callable=AsyncMock) as run,
            ):
                with self.assertRaises(ufw_router.HTTPException) as raised:
                    await ufw_router.toggle_ufw(
                        action="disable", user={"username": "admin"}
                    )

            self.assertEqual(raised.exception.status_code, 503)
            self.assertIn("manual_recovery_required", raised.exception.detail)
            self.assertFalse(os.path.exists(missing_directory))
            run.assert_not_awaited()

    async def test_missing_database_after_startup_blocks_firewall_mutations(self):
        os.remove(self.marker)
        os.remove(os.path.join(self.directory.name, "stats.db"))
        with patch.object(ufw_router, "run_ufw", new_callable=AsyncMock) as run:
            with self.assertRaises(ufw_router.HTTPException) as raised:
                await ufw_router.toggle_ufw(
                    action="disable", user={"username": "admin"}
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("manual_recovery_required", raised.exception.detail)
        run.assert_not_awaited()
        self.assertFalse(os.path.exists(os.path.join(self.directory.name, "stats.db")))

    async def test_fifo_database_fails_closed_without_blocking_the_request(self):
        os.remove(self.marker)
        database_path = os.path.join(self.directory.name, "stats.db")
        os.remove(database_path)
        os.mkfifo(database_path)

        with patch.object(ufw_router, "run_ufw", new_callable=AsyncMock) as run:
            with self.assertRaises(ufw_router.HTTPException) as raised:
                await asyncio.wait_for(
                    ufw_router.toggle_ufw(action="disable", user={"username": "admin"}),
                    timeout=1,
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertTrue(os.path.exists(database_path))
        run.assert_not_awaited()

    async def test_corrupt_database_after_startup_blocks_firewall_mutation(self):
        os.remove(self.marker)
        database_path = os.path.join(self.directory.name, "stats.db")
        with closing(sqlite3.connect(database_path)) as database:
            database.execute("CREATE TABLE corruption_probe (value TEXT)")
            database.executemany(
                "INSERT INTO corruption_probe VALUES (?)",
                [("x" * 6000,) for _ in range(40)],
            )
            database.commit()
            page_size = database.execute("PRAGMA page_size").fetchone()[0]

        with open(database_path, "r+b") as database:
            database.seek(page_size)
            database.write(b"\x00" * page_size)

        with patch.object(ufw_router, "run_ufw", new_callable=AsyncMock) as run:
            with self.assertRaises(ufw_router.HTTPException) as raised:
                await ufw_router.toggle_ufw(
                    action="disable", user={"username": "admin"}
                )

        self.assertEqual(raised.exception.status_code, 503)
        run.assert_not_awaited()

    async def test_marker_created_while_mutation_waits_for_lock_blocks_route(self):
        os.remove(self.marker)
        lock_attempted = asyncio.Event()
        original_try_acquire = recovery_guard._try_acquire_mutation_lock

        def observe_lock_attempt():
            descriptor = original_try_acquire()
            lock_attempted.set()
            return descriptor

        with patch.object(ufw_router, "run_ufw", new_callable=AsyncMock) as run:
            async with recovery_guard.firewall_mutation_guard():
                with patch.object(
                    recovery_guard,
                    "_try_acquire_mutation_lock",
                    side_effect=observe_lock_attempt,
                ):
                    waiting_mutation = asyncio.create_task(
                        ufw_router.toggle_ufw(
                            action="disable", user={"username": "admin"}
                        ),
                        context=contextvars.Context(),
                    )
                    await asyncio.wait_for(lock_attempted.wait(), timeout=1)
                    self.assertFalse(waiting_mutation.done())
                    with open(self.marker, "wb") as marker:
                        marker.write(self.marker_bytes)
                    os.chmod(self.marker, 0o640)

        with self.assertRaises(ufw_router.HTTPException) as raised:
            await asyncio.wait_for(waiting_mutation, timeout=1)
        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("manual_recovery_required", raised.exception.detail)
        run.assert_not_awaited()
        self.assert_marker_unchanged()

    async def test_status_and_startup_inspect_marker_under_shared_lock(self):
        for operation in (
            reload_router.get_recovery_status,
            main.inspect_recovery_state_on_startup,
        ):
            with self.subTest(operation=operation.__name__):
                if os.path.lexists(self.marker):
                    os.remove(self.marker)
                lock_attempted = asyncio.Event()
                original_try_acquire = recovery_guard._try_acquire_mutation_lock

                def observe_lock_attempt():
                    descriptor = original_try_acquire()
                    if descriptor is None:
                        lock_attempted.set()
                    return descriptor

                with patch.object(
                    recovery_guard,
                    "_try_acquire_mutation_lock",
                    side_effect=observe_lock_attempt,
                ):
                    async with recovery_guard.firewall_mutation_guard():
                        inspection = asyncio.create_task(
                            operation(user={"username": "admin"})
                            if operation is reload_router.get_recovery_status
                            else operation(),
                            context=contextvars.Context(),
                        )
                        await asyncio.wait_for(lock_attempted.wait(), timeout=1)
                        self.assertFalse(inspection.done())
                        with open(self.marker, "wb") as marker:
                            marker.write(self.marker_bytes)
                        os.chmod(self.marker, 0o640)

                    if operation is reload_router.get_recovery_status:
                        status = await asyncio.wait_for(inspection, timeout=1)
                        self.assertEqual(status["mode"], "manual_recovery_required")
                    else:
                        with self.assertLogs("backend.main", level="ERROR"):
                            await asyncio.wait_for(inspection, timeout=1)

                self.assert_marker_unchanged()

    async def test_replacing_legacy_lock_filename_cannot_bypass_directory_lock(self):
        legacy_lock_path = os.path.join(self.directory.name, ".firewall-mutation.lock")
        os.remove(self.marker)
        descriptors = recovery_guard._try_acquire_mutation_lock()
        self.assertIsNotNone(descriptors)
        descriptor, database_descriptor = descriptors
        try:
            os.symlink("unused-lock-target", legacy_lock_path)
            self.assertIsNone(recovery_guard._try_acquire_mutation_lock())
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(database_descriptor)
            os.close(descriptor)

        self.assertTrue(os.path.islink(legacy_lock_path))
        with open(self.marker, "wb") as marker:
            marker.write(self.marker_bytes)
        os.chmod(self.marker, 0o640)
        self.assert_marker_unchanged()

    async def test_data_directory_replaced_after_lock_acquisition_blocks_mutation(self):
        data_directory = os.path.join(self.directory.name, "data")
        moved_directory = os.path.join(self.directory.name, "data-before-replacement")
        os.mkdir(data_directory)
        shutil.copy2(
            os.path.join(self.directory.name, "stats.db"),
            os.path.join(data_directory, "stats.db"),
        )
        with patch.object(
            database_service, "DB_FILE", os.path.join(data_directory, "stats.db")
        ):
            database_service.init_db()
        marker_path = os.path.join(data_directory, "test_state.json")
        with open(marker_path, "wb") as marker:
            marker.write(self.marker_bytes)
        os.chmod(marker_path, 0o640)

        original_try_acquire = recovery_guard._try_acquire_mutation_lock

        def acquire_then_replace_directory():
            descriptor = original_try_acquire()
            os.rename(data_directory, moved_directory)
            os.mkdir(data_directory)
            shutil.copy2(
                os.path.join(moved_directory, "stats.db"),
                os.path.join(data_directory, "stats.db"),
            )
            return descriptor

        with (
            patch.object(filesystem_service, "TEST_STATE_FILE", marker_path),
            patch.object(
                recovery_guard,
                "_try_acquire_mutation_lock",
                side_effect=acquire_then_replace_directory,
            ),
            patch.object(ufw_router, "run_ufw", new_callable=AsyncMock) as run,
        ):
            with self.assertRaises(ufw_router.HTTPException) as raised:
                await ufw_router.toggle_ufw(
                    action="disable", user={"username": "admin"}
                )

        self.assertEqual(raised.exception.status_code, 503)
        run.assert_not_awaited()
        with open(os.path.join(moved_directory, "test_state.json"), "rb") as marker:
            self.assertEqual(marker.read(), self.marker_bytes)

    async def test_database_replaced_after_directory_lock_acquisition_blocks_mutation(
        self,
    ):
        os.remove(self.marker)
        database_path = os.path.join(self.directory.name, "stats.db")
        backup_path = os.path.join(self.directory.name, "stats.db.original")
        replacement_path = os.path.join(self.directory.name, "stats.db.replacement")
        shutil.copy2(database_path, replacement_path)
        original_try_acquire = recovery_guard._try_acquire_mutation_lock

        def acquire_then_replace_database():
            descriptor = original_try_acquire()
            os.replace(database_path, backup_path)
            shutil.copy2(backup_path, replacement_path)
            os.replace(replacement_path, database_path)
            return descriptor

        try:
            with (
                patch.object(
                    recovery_guard,
                    "_try_acquire_mutation_lock",
                    side_effect=acquire_then_replace_database,
                ),
                patch.object(ufw_router, "run_ufw", new_callable=AsyncMock) as run,
            ):
                with self.assertRaises(ufw_router.HTTPException) as raised:
                    await ufw_router.toggle_ufw(
                        action="disable", user={"username": "admin"}
                    )

            self.assertEqual(raised.exception.status_code, 503)
            run.assert_not_awaited()
        finally:
            if os.path.exists(backup_path):
                os.replace(backup_path, database_path)

    async def test_child_task_cannot_inherit_mutation_admission(self):
        os.remove(self.marker)
        with patch.object(subprocess_service, "run") as run:
            async with recovery_guard.firewall_mutation_guard():
                child = asyncio.create_task(subprocess_service.run_ufw("disable"))
                with self.assertRaises(ufw_router.HTTPException) as raised:
                    await child

        self.assertEqual(raised.exception.status_code, 503)
        run.assert_not_called()

    async def test_marker_created_after_admission_blocks_command_launch(self):
        os.remove(self.marker)
        with patch.object(subprocess_service, "run") as run:
            async with recovery_guard.firewall_mutation_guard():
                with open(self.marker, "wb") as marker:
                    marker.write(self.marker_bytes)
                os.chmod(self.marker, 0o640)

                with self.assertRaises(ufw_router.HTTPException) as raised:
                    await subprocess_service._run_command(["ufw", "disable"])

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("manual_recovery_required", raised.exception.detail)
        run.assert_not_called()
        self.assert_marker_unchanged()

    async def test_marker_rechecked_at_thread_boundary_before_subprocess(self):
        os.remove(self.marker)
        original_runner = subprocess_service.run_to_thread_to_completion

        async def create_marker_before_worker(function, *args, **kwargs):
            with open(self.marker, "wb") as marker:
                marker.write(self.marker_bytes)
            os.chmod(self.marker, 0o640)
            return await original_runner(function, *args, **kwargs)

        with (
            patch.object(subprocess_service, "run") as run,
            patch.object(
                subprocess_service,
                "run_to_thread_to_completion",
                side_effect=create_marker_before_worker,
            ),
        ):
            async with recovery_guard.firewall_mutation_guard():
                with self.assertRaises(ufw_router.HTTPException) as raised:
                    await subprocess_service._run_command(["ufw", "disable"])

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("manual_recovery_required", raised.exception.detail)
        run.assert_not_called()
        self.assert_marker_unchanged()

    async def test_startup_refuses_database_replaced_after_database_validation(self):
        os.remove(self.marker)
        database_path = os.path.join(self.directory.name, "stats.db")
        replacement_path = os.path.join(self.directory.name, "stats.db.replacement")
        with patch.object(database_service, "DB_FILE", database_path):
            database_service.init_db()
            open(replacement_path, "wb").close()
            os.replace(replacement_path, database_path)

            with self.assertRaises(ufw_router.HTTPException) as raised:
                await main.inspect_recovery_state_on_startup()

        self.assertEqual(raised.exception.status_code, 503)

    async def test_every_firewall_mutation_route_is_blocked_before_side_effects(self):
        user = {"username": "admin"}
        routes = (
            (ufw_router.toggle_ufw, {"action": "disable", "user": user}),
            (
                ufw_router.add_rule,
                {
                    "action": "allow",
                    "port": "22",
                    "proto": "tcp",
                    "ip": "",
                    "user": user,
                },
            ),
            (ufw_router.delete_rule, {"rule_id": "1", "user": user}),
            (ufw_router.ban_ip, {"ip": "192.0.2.1", "user": user}),
            (ufw_router.reload_firewall, {"user": user}),
            (
                fail2ban_router.unban_ip,
                {"ip": "192.0.2.1", "jail": "sshd", "user": user},
            ),
            (
                admin_router.restore_snapshot_route,
                {"name": "known-snapshot", "user": user},
            ),
        )
        with (
            patch.object(ufw_router, "run_ufw", new_callable=AsyncMock) as ufw,
            patch.object(
                filesystem_service, "create_snapshot", new_callable=AsyncMock
            ) as snapshot,
            patch.object(
                fail2ban_router, "run_fail2ban", new_callable=AsyncMock
            ) as fail2ban,
            patch.object(
                filesystem_service,
                "restore_snapshot",
                new_callable=AsyncMock,
            ) as restore,
        ):
            for route, kwargs in routes:
                with self.subTest(route=route.__name__):
                    with self.assertRaises(ufw_router.HTTPException) as raised:
                        await route(**kwargs)
                    self.assertEqual(raised.exception.status_code, 503)
                    self.assertIn("manual_recovery_required", raised.exception.detail)

            ufw.assert_not_awaited()
            snapshot.assert_not_awaited()
            fail2ban.assert_not_awaited()
            restore.assert_not_awaited()
            self.assert_marker_unchanged()

    async def test_snapshot_restore_service_refuses_before_touching_target(self):
        snapshot = os.path.join(self.directory.name, "snapshot")
        os.mkdir(snapshot)
        target = os.path.join(self.directory.name, "target-sentinel")
        with open(target, "wb") as sentinel:
            sentinel.write(b"must remain untouched")

        with (
            patch.object(filesystem_service, "UFW_BACKUP_DIR", self.directory.name),
        ):
            with self.assertRaises(ufw_router.HTTPException) as raised:
                await filesystem_service.restore_snapshot("snapshot")
        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("manual_recovery_required", raised.exception.detail)

        with open(target, "rb") as sentinel:
            self.assertEqual(sentinel.read(), b"must remain untouched")
        self.assert_marker_unchanged()


if __name__ == "__main__":
    unittest.main()
