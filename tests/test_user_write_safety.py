"""User management must not overwrite accounts or resurrect deleted users."""

import asyncio
import concurrent.futures
import os
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.routers import admin_router
from backend.services import filesystem_service


class UserWriteSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.database = self.root / "stats.db"
        for item in (
            patch.object(filesystem_service, "DATA_DIR", str(self.root)),
            patch.object(
                filesystem_service, "USER_DATA_FILE", str(self.root / "users.json")
            ),
            patch.object(admin_router, "log_action"),
        ):
            item.start()
            self.addCleanup(item.stop)
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(
                "CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, role TEXT)"
            )
            connection.executemany(
                "INSERT INTO users VALUES (?, ?, ?)",
                [("root", "root-hash", "superadmin"), ("victim", "old-hash", "admin")],
            )

    def rows(self):
        with closing(sqlite3.connect(self.database)) as connection:
            return connection.execute(
                "SELECT username, password, role FROM users ORDER BY username"
            ).fetchall()

    def test_existing_account_cannot_be_overwritten_or_demoted(self):
        before = self.rows()
        with patch.object(admin_router, "hash_password", return_value="new-hash"):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    admin_router.add_user(
                        username="root",
                        password="fixture-only-password",
                        user={"username": "root", "role": "superadmin"},
                    )
                )
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(self.rows(), before)

    def test_revoked_actor_cannot_add_a_user_after_authentication(self):
        before = self.rows()
        with patch.object(admin_router, "hash_password", return_value="new-hash"):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    admin_router.add_user(
                        username="new-user",
                        password="fixture-only-password",
                        user={"username": "revoked", "role": "superadmin"},
                    )
                )
        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(self.rows(), before)

    def test_concurrent_add_does_not_resurrect_a_deleted_account(self):
        barrier = threading.Barrier(2)
        deleted = threading.Event()
        original_load = filesystem_service.load_users
        original_save = filesystem_service.save_users

        def synchronize_reads():
            users = original_load()
            barrier.wait(timeout=5)
            return users

        def order_legacy_writes(users):
            if "victim" not in users:
                original_save(users)
                deleted.set()
            else:
                if not deleted.wait(timeout=5):
                    raise TimeoutError("delete did not finish")
                original_save(users)

        actor = {"username": "root", "role": "superadmin"}
        with (
            patch.object(admin_router, "load_users", side_effect=synchronize_reads),
            patch.object(
                admin_router, "save_users", side_effect=order_legacy_writes, create=True
            ),
            patch.object(admin_router, "hash_password", return_value="new-hash"),
            concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool,
        ):
            add = pool.submit(
                lambda: asyncio.run(
                    admin_router.add_user(
                        username="new-user",
                        password="fixture-only-password",
                        user=actor,
                    )
                )
            )
            remove = pool.submit(
                lambda: asyncio.run(
                    admin_router.del_user(username="victim", user=actor)
                )
            )
            self.assertEqual(add.result(timeout=10), {"status": "success"})
            self.assertEqual(remove.result(timeout=10), {"status": "success"})

        self.assertEqual(
            self.rows(),
            [("new-user", "new-hash", "admin"), ("root", "root-hash", "superadmin")],
        )


if __name__ == "__main__":
    unittest.main()
