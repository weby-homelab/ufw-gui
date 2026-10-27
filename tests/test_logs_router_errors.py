"""Log and statistics routes isolate I/O and report safe diagnostics."""

import asyncio
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.routers import logs_router


class LogsRouterErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_log_file_read_is_offloaded_and_parsed(self):
        sample = (
            "Jan 01 00:00:00 host kernel: [UFW BLOCK] SRC=192.0.2.1 PROTO=TCP DPT=22\n"
        )
        with (
            patch.object(
                logs_router.os.path,
                "exists",
                side_effect=lambda path: path == "/var/log/ufw.log",
            ),
            patch("builtins.open", mock_open(read_data=sample)),
            patch.object(
                logs_router.asyncio, "to_thread", wraps=asyncio.to_thread
            ) as to_thread,
        ):
            result = await logs_router.get_ufw_logs(user={"username": "admin"})

        self.assertEqual(result["logs"][0]["src"], "192.0.2.1")
        to_thread.assert_awaited_once()

    async def test_log_read_io_failure_returns_safe_diagnostic(self):
        with (
            patch.object(
                logs_router.os.path,
                "exists",
                side_effect=lambda path: path == "/var/log/ufw.log",
            ),
            patch("builtins.open", side_effect=PermissionError("private log sentinel")),
            self.assertLogs("backend.routers.logs_router", level="WARNING") as logs,
        ):
            result = await logs_router.get_ufw_logs(user={"username": "admin"})

        self.assertEqual(result["logs"], [])
        self.assertEqual(result["error"], "UFW logs are unavailable.")
        self.assertNotIn("private log sentinel", "\n".join(logs.output))

    async def test_invalid_utf8_does_not_break_valid_firewall_log_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ufw.log"
            path.write_bytes(
                b"invalid-byte: \xff\n"
                b"Jan 01 00:00:00 host kernel: [UFW BLOCK] "
                b"SRC=192.0.2.1 PROTO=TCP DPT=22\n"
            )
            read_log_lines = logs_router._read_log_lines
            with (
                patch.object(logs_router.os.path, "exists", return_value=True),
                patch.object(
                    logs_router,
                    "_read_log_lines",
                    side_effect=lambda _: read_log_lines(str(path)),
                ),
            ):
                result = await logs_router.get_ufw_logs(user={"username": "admin"})

        self.assertEqual(result["logs"][0]["src"], "192.0.2.1")

    async def test_stats_database_failure_returns_safe_diagnostic(self):
        with (
            patch.object(
                logs_router,
                "get_stats_last_24h",
                side_effect=sqlite3.OperationalError("private db sentinel"),
            ),
            self.assertLogs("backend.routers.logs_router", level="WARNING") as logs,
        ):
            result = await logs_router.get_stats(user={"username": "admin"})

        self.assertEqual(result["hourly"], [])
        self.assertEqual(result["error"], "Statistics are unavailable.")
        self.assertNotIn("private db sentinel", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
