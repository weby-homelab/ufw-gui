"""Authentication setup must fail closed when user data cannot be read."""
import asyncio
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.routers import auth_router
from backend.services import filesystem_service as storage


class AuthFailureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.p1 = patch.object(storage, "DATA_DIR", str(self.root))
        self.p2 = patch.object(storage, "USER_DATA_FILE", str(self.root / "users.json"))
        self.p1.start()
        self.p2.start()
        self.addCleanup(self.p1.stop)
        self.addCleanup(self.p2.stop)

    def test_missing_database_does_not_look_like_empty_users(self):
        with self.assertRaises(RuntimeError):
            storage.load_users()

    def test_broken_database_does_not_look_like_empty_users(self):
        (self.root / "stats.db").write_text("not a database", encoding="utf-8")
        with self.assertRaises(sqlite3.DatabaseError):
            storage.load_users()

    def test_corrupt_legacy_users_does_not_allow_setup(self):
        (self.root / "users.json").write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            storage.load_users()

    def test_valid_empty_database_is_still_setup_needed(self):
        with sqlite3.connect(self.root / "stats.db") as db:
            db.execute("CREATE TABLE users (username TEXT, password TEXT, role TEXT)")
        self.assertEqual(storage.load_users(), {})

    def test_setup_does_not_write_when_users_cannot_be_read(self):
        with patch.object(auth_router, "load_users", side_effect=RuntimeError("read failed")):
            with patch.object(auth_router, "save_users") as save:
                with self.assertRaises(RuntimeError):
                    asyncio.run(auth_router.setup_admin(username="admin", password="pw"))
                save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
