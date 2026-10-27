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
        with (
            patch.object(
                ufw_router, "run_ufw", new_callable=AsyncMock, side_effect=failure
            ),
            self.assertRaises(HTTPException) as raised,
        ):
            await ufw_router.get_status(user={"username": "admin"})

        self.assertIs(raised.exception, failure)

    async def test_command_failure_is_unknown_not_inactive(self):
        failure = HTTPException(status_code=500, detail="safe command failure")
        with (
            patch.object(
                ufw_router, "run_ufw", new_callable=AsyncMock, side_effect=failure
            ),
            self.assertLogs("backend.routers.ufw_router", level="WARNING"),
        ):
            result = await ufw_router.get_status(user={"username": "admin"})

        self.assertEqual(
            result,
            {"status": "unknown", "error_code": "ufw_command_failed"},
        )

    async def test_empty_or_unrecognized_output_is_unknown_not_inactive(self):
        for output in (
            "",
            "UFW status unavailable",
            "Default: deny (incoming)",
            "Status: active\nStatus: inactive",
        ):
            with self.subTest(output=output):
                with (
                    patch.object(
                        ufw_router,
                        "run_ufw",
                        new_callable=AsyncMock,
                        return_value=output,
                    ),
                    self.assertLogs("backend.routers.ufw_router", level="WARNING"),
                ):
                    result = await ufw_router.get_status(user={"username": "admin"})

                self.assertEqual(
                    result,
                    {"status": "unknown", "error_code": "ufw_status_unrecognized"},
                )

    async def test_only_explicit_ufw_status_lines_map_to_state(self):
        for output, expected in (
            ("Status: active\nLogging: on", "running"),
            ("Status: inactive\nLogging: off", "inactive"),
        ):
            with self.subTest(expected=expected):
                with patch.object(
                    ufw_router,
                    "run_ufw",
                    new_callable=AsyncMock,
                    return_value=output,
                ):
                    result = await ufw_router.get_status(user={"username": "admin"})

                self.assertEqual(result, {"status": expected})

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
            result,
            {"status": "unknown", "error_code": "ufw_command_unavailable"},
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
