"""Fail2Ban status errors are visible without leaking subprocess details."""

import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.routers import fail2ban_router


class Fail2BanStatusErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_sanitized_http_failure_is_not_reported_as_empty_status(self):
        failure = HTTPException(status_code=503, detail="safe daemon failure")
        with patch.object(
            fail2ban_router, "run_fail2ban", new_callable=AsyncMock, side_effect=failure
        ):
            with self.assertRaises(HTTPException) as raised:
                await fail2ban_router.get_f2b_status(user={"username": "admin"})

        self.assertIs(raised.exception, failure)

    async def test_process_io_failure_returns_safe_unavailable_response_and_log(self):
        with (
            patch.object(
                fail2ban_router,
                "run_fail2ban",
                new_callable=AsyncMock,
                side_effect=FileNotFoundError("private socket path sentinel"),
            ),
            self.assertLogs("backend.routers.fail2ban_router", level="WARNING") as logs,
        ):
            with self.assertRaises(HTTPException) as raised:
                await fail2ban_router.get_f2b_status(user={"username": "admin"})

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "Fail2Ban status is unavailable.")
        self.assertNotIn("private socket path sentinel", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
