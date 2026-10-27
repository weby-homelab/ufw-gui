"""Subprocess error responses never disclose command stderr."""

import os
import unittest
from subprocess import CalledProcessError
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.services import subprocess_service


class SubprocessErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_ufw_stderr_is_suppressed_from_logs_and_response(self):
        private_stderr = "private-ufw-stderr-sentinel"
        failure = CalledProcessError(1, ["ufw", "status"], stderr=private_stderr)

        with (
            patch.object(
                subprocess_service,
                "_run_command",
                new_callable=AsyncMock,
                side_effect=failure,
            ),
            self.assertLogs(
                "backend.services.subprocess_service", level="WARNING"
            ) as logs,
            self.assertRaises(HTTPException) as raised,
        ):
            await subprocess_service.run_ufw("status")

        self.assertEqual(raised.exception.status_code, 500)
        self.assertNotIn(private_stderr, raised.exception.detail)
        self.assertNotIn(private_stderr, "\n".join(logs.output))

    async def test_fail2ban_stderr_is_suppressed_from_logs_and_response(self):
        private_stderr = "private-fail2ban-stderr-sentinel"
        failure = CalledProcessError(
            1, ["fail2ban-client", "status"], stderr=private_stderr
        )

        with (
            patch.object(
                subprocess_service,
                "_run_command",
                new_callable=AsyncMock,
                side_effect=failure,
            ),
            self.assertLogs(
                "backend.services.subprocess_service", level="WARNING"
            ) as logs,
            self.assertRaises(HTTPException) as raised,
        ):
            await subprocess_service.run_fail2ban("status")

        self.assertEqual(raised.exception.status_code, 500)
        self.assertNotIn(private_stderr, raised.exception.detail)
        self.assertNotIn(private_stderr, "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
