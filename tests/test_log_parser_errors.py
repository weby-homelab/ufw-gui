"""Background log parsing handles expected I/O/database failures safely."""

import asyncio
import os
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.services import log_parser_service


class LogParserErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_log_files_use_module_logger(self):
        with (
            patch.object(log_parser_service, "LOG_PATHS", []),
            self.assertLogs(
                "backend.services.log_parser_service", level="WARNING"
            ) as logs,
        ):
            await log_parser_service.start_log_parser()

        self.assertIn("No log files found", "\n".join(logs.output))

    async def test_initial_stat_failure_logs_only_exception_class_then_cancels(self):
        with (
            patch.object(log_parser_service, "LOG_PATHS", ["/private/log"]),
            patch.object(log_parser_service.os.path, "exists", return_value=True),
            patch.object(
                log_parser_service.os,
                "stat",
                side_effect=PermissionError("private stat sentinel"),
            ),
            patch.object(
                log_parser_service.asyncio,
                "sleep",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError,
            ),
            self.assertLogs(
                "backend.services.log_parser_service", level="WARNING"
            ) as logs,
        ):
            await log_parser_service.start_log_parser()

        self.assertNotIn("private stat sentinel", "\n".join(logs.output))

    async def test_log_read_os_error_is_logged_safely(self):
        with (
            patch.object(
                log_parser_service.asyncio,
                "to_thread",
                new_callable=AsyncMock,
                side_effect=PermissionError("private read sentinel"),
            ),
            self.assertLogs(
                "backend.services.log_parser_service", level="WARNING"
            ) as logs,
        ):
            await log_parser_service.parse_logs_range("/private/log", 0, 32)

        self.assertNotIn("private read sentinel", "\n".join(logs.output))

    async def test_database_write_error_is_logged_without_log_contents(self):
        sample = (
            "Jan 01 00:00:00 host kernel: [UFW BLOCK] "
            "SRC=198.51.100.77 PROTO=TCP DPT=22\n"
        )
        with (
            patch.object(
                log_parser_service.asyncio,
                "to_thread",
                new_callable=AsyncMock,
                side_effect=[sample, sqlite3.OperationalError("private db sentinel")],
            ),
            self.assertLogs(
                "backend.services.log_parser_service", level="ERROR"
            ) as logs,
        ):
            await log_parser_service.parse_logs_range("/private/log", 0, len(sample))

        output = "\n".join(logs.output)
        self.assertNotIn("private db sentinel", output)
        self.assertNotIn("198.51.100.77", output)

    async def test_parser_cancellation_exits_cleanly(self):
        with (
            patch.object(log_parser_service, "LOG_PATHS", ["/private/log"]),
            patch.object(log_parser_service.os.path, "exists", return_value=True),
            patch.object(
                log_parser_service.os,
                "stat",
                return_value=SimpleNamespace(st_size=0, st_ino=1),
            ),
            patch.object(
                log_parser_service.asyncio,
                "sleep",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError,
            ),
        ):
            await log_parser_service.start_log_parser()


if __name__ == "__main__":
    unittest.main()
