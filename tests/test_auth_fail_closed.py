"""Authentication setup must fail closed when user data cannot be read."""
import asyncio
import concurrent.futures
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.routers import auth_router
from backend.services import filesystem_service as storage
from backend.services import auth_service


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
        with sqlite3.connect(self.root / "stats.db") as db:
            db.execute("CREATE TABLE users (username TEXT, password TEXT, role TEXT)")
        (self.root / "users.json").write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            storage.load_users()

    def test_valid_empty_database_is_still_setup_needed(self):
        with sqlite3.connect(self.root / "stats.db") as db:
            db.execute("CREATE TABLE users (username TEXT, password TEXT, role TEXT)")
        self.assertEqual(storage.load_users(), {})

    def test_setup_does_not_write_when_users_cannot_be_read(self):
        with patch.object(auth_router, "load_users", side_effect=RuntimeError("read failed")):
            with patch.object(auth_router, "create_initial_admin") as save:
                with self.assertRaises(RuntimeError):
                    asyncio.run(auth_router.setup_admin(username="admin", password="pw"))
                save.assert_not_called()


    def test_concurrent_setup_cannot_replace_existing_admin(self):
        with sqlite3.connect(self.root / "stats.db") as db:
            db.execute("CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, role TEXT)")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda name: storage.create_initial_admin(name, "hash"), ["one", "two"]))
        self.assertEqual(sorted(results), [False, True])
        with sqlite3.connect(self.root / "stats.db") as db:
            rows = db.execute("SELECT username, role FROM users").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "superadmin")
        self.assertFalse(storage.create_initial_admin("third", "hash"))
        with sqlite3.connect(self.root / "stats.db") as db:
            self.assertEqual(db.execute("SELECT username, role FROM users").fetchall(), rows)



    def test_legacy_migration_preserves_existing_accounts(self):
        with sqlite3.connect(self.root / "stats.db") as db:
            db.execute("CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, role TEXT)")
            db.execute("INSERT INTO users VALUES (?, ?, ?)", ("existing", "old-hash", "superadmin"))
        legacy = {"existing": {"password": "other-hash"}, "legacy": {"password": "legacy-hash"}}
        (self.root / "users.json").write_text(json.dumps(legacy), encoding="utf-8")
        users = storage.load_users()
        self.assertEqual(users["existing"]["password"], "old-hash")
        self.assertEqual(users["legacy"]["password"], "legacy-hash")
        self.assertFalse((self.root / "users.json").exists())

    def test_failed_legacy_migration_rolls_back_and_keeps_source(self):
        with sqlite3.connect(self.root / "stats.db") as db:
            db.execute("CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, role TEXT)")
        legacy = {"first": {"password": "valid-hash"}, "second": {}}
        (self.root / "users.json").write_text(json.dumps(legacy), encoding="utf-8")
        with self.assertRaises(KeyError):
            storage.load_users()
        self.assertTrue((self.root / "users.json").exists())
        with sqlite3.connect(self.root / "stats.db") as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)

    def test_access_and_refresh_tokens_remain_compatible(self):
        token = auth_service.create_access_token("alice", "admin")
        refresh = auth_service.create_refresh_token("alice")
        self.assertEqual(auth_service.verify_access_token(token)["sub"], "alice")
        self.assertEqual(auth_service.verify_refresh_token(refresh)["sub"], "alice")
        self.assertIsNone(auth_service.verify_access_token(refresh))
        self.assertIsNone(auth_service.verify_refresh_token(token))
        self.assertIsNone(auth_service.verify_access_token("invalid"))

if __name__ == "__main__":
    unittest.main()
