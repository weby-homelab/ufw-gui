"""Configuration reads fall back only for known storage/format errors."""

import os
import tempfile
import unittest
from unittest.mock import mock_open, patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.services import filesystem_service


class ConfigLoadErrorTests(unittest.TestCase):
    def test_settings_save_does_not_recreate_missing_storage_directory(self):
        with tempfile.TemporaryDirectory() as parent:
            missing_directory = os.path.join(parent, "missing-data")
            with (
                patch.object(filesystem_service, "DATA_DIR", missing_directory),
                patch.object(
                    filesystem_service,
                    "CONFIG_FILE",
                    os.path.join(missing_directory, "config.json"),
                ),
            ):
                with self.assertRaises(FileNotFoundError):
                    filesystem_service.save_config({"tg_chat_id": "1"})

            self.assertFalse(os.path.exists(missing_directory))

    def test_expected_read_error_returns_empty_config_without_leaking_error(self):
        with (
            patch.object(filesystem_service.os.path, "exists", return_value=True),
            patch(
                "builtins.open",
                side_effect=PermissionError("private config sentinel"),
            ),
            self.assertLogs(
                "backend.services.filesystem_service", level="WARNING"
            ) as logs,
        ):
            self.assertEqual(filesystem_service.load_config(), {})

        self.assertNotIn("private config sentinel", "\n".join(logs.output))

    def test_invalid_json_returns_empty_config_without_logging_contents(self):
        with (
            patch.object(filesystem_service.os.path, "exists", return_value=True),
            patch("builtins.open", mock_open(read_data='{"tg_token":"sentinel')),
            self.assertLogs(
                "backend.services.filesystem_service", level="WARNING"
            ) as logs,
        ):
            self.assertEqual(filesystem_service.load_config(), {})

        self.assertNotIn("sentinel", "\n".join(logs.output))

    def test_unexpected_programming_error_is_not_hidden(self):
        with (
            patch.object(filesystem_service.os.path, "exists", return_value=True),
            patch("builtins.open", side_effect=RuntimeError("programming error")),
        ):
            with self.assertRaisesRegex(RuntimeError, "programming error"):
                filesystem_service.load_config()


if __name__ == "__main__":
    unittest.main()
