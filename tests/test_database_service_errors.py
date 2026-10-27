"""Database and Telegram diagnostics must not disclose error payloads/secrets."""

import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

import requests

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.services import database_service


class DatabaseServiceErrorTests(unittest.TestCase):
    def test_database_initialization_does_not_recreate_missing_data_mount(self):
        with tempfile.TemporaryDirectory() as parent:
            missing_directory = os.path.join(parent, "missing-data")
            with (
                patch.object(database_service, "DATA_DIR", missing_directory),
                patch.object(
                    database_service,
                    "DB_FILE",
                    os.path.join(missing_directory, "stats.db"),
                ),
            ):
                with self.assertRaises(RuntimeError):
                    database_service.init_db()

            self.assertFalse(os.path.exists(missing_directory))

    def test_database_initialization_requires_an_existing_regular_database_file(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            with (
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                with self.assertRaises(RuntimeError):
                    database_service.init_db()

            self.assertFalse(os.path.exists(database_path))

    def test_database_initialization_refuses_an_empty_replacement_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            open(database_path, "wb").close()
            with (
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                with self.assertRaises(RuntimeError):
                    database_service.init_db()

            with closing(sqlite3.connect(database_path)) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
            self.assertFalse(tables)

    def test_database_initialization_rejects_missing_auth_and_unique_constraints(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            with closing(sqlite3.connect(database_path)) as database:
                database.executescript(
                    "CREATE TABLE drops (id INTEGER, ts TIMESTAMP, src TEXT, "
                    "proto TEXT, port TEXT);"
                    "CREATE TABLE audit_logs (id INTEGER, ts TIMESTAMP, "
                    "username TEXT, action TEXT, details TEXT);"
                    "CREATE TABLE users (username TEXT, password TEXT, role TEXT);"
                )

            with (
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                with self.assertRaises(RuntimeError):
                    database_service.init_db()

    def test_database_initialization_rejects_partial_unique_constraint(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            with closing(sqlite3.connect(database_path)) as database:
                database.executescript(
                    "CREATE TABLE drops (id INTEGER PRIMARY KEY, ts TIMESTAMP, "
                    "src TEXT, proto TEXT, port TEXT);"
                    "CREATE UNIQUE INDEX drops_partial_unique ON drops(ts, src, port) "
                    "WHERE id < 0;"
                    "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, ts TIMESTAMP, "
                    "username TEXT, action TEXT, details TEXT);"
                    "CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, role TEXT);"
                )

            with (
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                with self.assertRaises(RuntimeError):
                    database_service.init_db()

    def test_database_initialization_rejects_corrupt_pages_even_when_schema_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            with (
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                database_service.initialize_empty_database()

                with closing(sqlite3.connect(database_path)) as connection:
                    connection.execute("CREATE TABLE corruption_probe (value TEXT)")
                    connection.executemany(
                        "INSERT INTO corruption_probe VALUES (?)",
                        [("x" * 6000,) for _ in range(40)],
                    )
                    connection.commit()
                    page_count = connection.execute("PRAGMA page_count").fetchone()[0]
                    page_size = connection.execute("PRAGMA page_size").fetchone()[0]

                with open(database_path, "r+b") as database:
                    self.assertGreaterEqual(page_count, 2)
                    database.seek(page_size)
                    database.write(b"\x00" * page_size)

                with self.assertRaises(RuntimeError):
                    database_service.init_db()

    def test_database_read_does_not_create_missing_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            with patch.object(database_service, "DB_FILE", database_path):
                with self.assertRaises(sqlite3.Error):
                    database_service.get_recent_drops()
            self.assertFalse(os.path.exists(database_path))

    def test_explicit_bootstrap_creates_schema_and_startup_accepts_it(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            with (
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                database_service.initialize_empty_database()
                database_service.init_db()

            with closing(sqlite3.connect(database_path)) as connection:
                self.assertTrue(database_service._has_required_schema(connection))

    def test_startup_validation_does_not_modify_database_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            with (
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                database_service.initialize_empty_database()
                with open(database_path, "rb") as database:
                    before = database.read()
                database_service.init_db()
                with open(database_path, "rb") as database:
                    after = database.read()

            self.assertEqual(after, before)

    def test_explicit_bootstrap_refuses_to_replace_existing_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            original = b"preserve existing database bytes"
            with open(database_path, "wb") as database:
                database.write(original)
            with (
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                with self.assertRaises(RuntimeError):
                    database_service.initialize_empty_database()
            with open(database_path, "rb") as database:
                self.assertEqual(database.read(), original)

    def test_explicit_bootstrap_refuses_existing_directory_with_legacy_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            marker_path = os.path.join(directory, "test_state.json")
            with open(marker_path, "wb") as marker:
                marker.write(b"do not erase unresolved legacy evidence")
            with (
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(
                    database_service, "DB_FILE", os.path.join(directory, "stats.db")
                ),
            ):
                with self.assertRaises(RuntimeError):
                    database_service.initialize_empty_database()

            self.assertFalse(os.path.exists(os.path.join(directory, "stats.db")))
            with open(marker_path, "rb") as marker:
                self.assertEqual(
                    marker.read(), b"do not erase unresolved legacy evidence"
                )

    def test_explicit_bootstrap_detects_evidence_added_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            marker_path = os.path.join(directory, "test_state.json")
            original_listdir = os.listdir
            calls = 0

            def add_marker_before_final_check(path):
                nonlocal calls
                calls += 1
                if calls == 2:
                    with open(marker_path, "wb") as marker:
                        marker.write(b"new unresolved evidence")
                return original_listdir(path)

            with (
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(
                    database_service, "DB_FILE", os.path.join(directory, "stats.db")
                ),
                patch.object(
                    database_service.os,
                    "listdir",
                    side_effect=add_marker_before_final_check,
                ),
            ):
                with self.assertRaises(RuntimeError):
                    database_service.initialize_empty_database()

            self.assertFalse(os.path.exists(os.path.join(directory, "stats.db")))
            with open(marker_path, "rb") as marker:
                self.assertEqual(marker.read(), b"new unresolved evidence")

    def test_audit_database_failure_is_logged_without_action_or_exception_text(self):
        with (
            patch.object(
                database_service.sqlite3,
                "connect",
                side_effect=sqlite3.OperationalError("private database sentinel"),
            ),
            patch.object(database_service._tg_executor, "submit"),
            self.assertLogs("backend.services.database_service", level="ERROR") as logs,
        ):
            database_service.log_action(
                "private-user", "PRIVATE_ACTION", "private-details"
            )

        output = "\n".join(logs.output)
        for private_value in (
            "private database sentinel",
            "private-user",
            "PRIVATE_ACTION",
            "private-details",
        ):
            self.assertNotIn(private_value, output)

    def test_executor_shutdown_error_is_logged_without_action_details(self):
        with tempfile.TemporaryDirectory() as directory:
            db_file = os.path.join(directory, "stats.db")
            with closing(sqlite3.connect(db_file)) as connection, connection:
                connection.execute(
                    "CREATE TABLE audit_logs "
                    "(id INTEGER PRIMARY KEY, ts TEXT, username TEXT, action TEXT, details TEXT)"
                )

            with (
                patch.object(database_service, "DB_FILE", db_file),
                patch.object(
                    database_service._tg_executor,
                    "submit",
                    side_effect=RuntimeError("executor private sentinel"),
                ),
                self.assertLogs(
                    "backend.services.database_service", level="ERROR"
                ) as logs,
            ):
                database_service.log_action(
                    "private-user", "PRIVATE_ACTION", "private-details"
                )

        output = "\n".join(logs.output)
        for private_value in (
            "executor private sentinel",
            "private-user",
            "PRIVATE_ACTION",
            "private-details",
        ):
            self.assertNotIn(private_value, output)

    def test_telegram_transport_failure_does_not_log_token_or_request_url(self):
        with tempfile.TemporaryDirectory() as directory:
            with open(
                os.path.join(directory, "config.json"), "w", encoding="utf-8"
            ) as cfg:
                json.dump({"tg_token": "fake", "tg_chat_id": "7"}, cfg)

            with (
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(
                    database_service.requests,
                    "post",
                    side_effect=requests.ConnectionError(
                        "request exception private transport sentinel"
                    ),
                ),
                self.assertLogs(
                    "backend.services.database_service", level="ERROR"
                ) as logs,
            ):
                database_service._send_tg_alert(
                    "private-user", "PRIVATE_ACTION", "private-details"
                )

        output = "\n".join(logs.output)
        for private_value in (
            "request exception private transport sentinel",
            "fake",
            "private-user",
            "PRIVATE_ACTION",
            "private-details",
        ):
            self.assertNotIn(private_value, output)


if __name__ == "__main__":
    unittest.main()
