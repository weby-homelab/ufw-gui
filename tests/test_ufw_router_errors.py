"""UFW read failures remain diagnosable without exposing raw subprocess errors."""

import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.routers import ufw_router


class UfwRouterErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_sanitized_http_status_failure_is_not_hidden_as_unknown(self):
        failure = HTTPException(status_code=503, detail="safe UFW failure")
        with patch.object(
            ufw_router, "run_ufw", new_callable=AsyncMock, side_effect=failure
        ):
            with self.assertRaises(HTTPException) as raised:
                await ufw_router.get_status(user={"username": "admin"})

        self.assertIs(raised.exception, failure)

    async def test_status_os_error_returns_unknown_with_safe_diagnostic(self):
        with (
            patch.object(
                ufw_router,
                "run_ufw",
                new_callable=AsyncMock,
                side_effect=PermissionError("private UFW sentinel"),
            ),
            self.assertLogs("backend.routers.ufw_router", level="WARNING") as logs,
        ):
            result = await ufw_router.get_status(user={"username": "admin"})

        self.assertEqual(
            result, {"status": "unknown", "error": "UFW status is unavailable."}
        )
        self.assertNotIn("private UFW sentinel", "\n".join(logs.output))

    async def test_rules_os_error_returns_safe_diagnostic(self):
        with (
            patch.object(
                ufw_router,
                "run_ufw",
                new_callable=AsyncMock,
                side_effect=FileNotFoundError("private executable sentinel"),
            ),
            self.assertLogs("backend.routers.ufw_router", level="WARNING") as logs,
        ):
            result = await ufw_router.get_rules(user={"username": "admin"})

        self.assertEqual(result["rules"], [])
        self.assertEqual(result["error"], "Failed to fetch rules. Check system logs.")
        self.assertNotIn("private executable sentinel", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
