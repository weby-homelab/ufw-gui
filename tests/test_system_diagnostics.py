"""Read-only diagnostics for the host UFW/Fail2Ban integration."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.services import system_diagnostics


def collect(which="/usr/sbin/ufw", isdir=True, ismount=True, exists=True):
    with (
        patch.object(system_diagnostics.shutil, "which", return_value=which),
        patch.object(system_diagnostics.os.path, "isdir", return_value=isdir),
        patch.object(system_diagnostics.os.path, "ismount", return_value=ismount),
        patch.object(system_diagnostics.os.path, "exists", return_value=exists),
    ):
        return system_diagnostics.collect_diagnostics()


class SystemDiagnosticsTests(unittest.TestCase):
    def test_healthy_integration_has_no_hints(self):
        result = collect()

        self.assertTrue(result["ufw"]["binary_present"])
        self.assertTrue(result["ufw"]["config_dir_present"])
        self.assertTrue(result["ufw"]["config_dir_mounted"])
        self.assertTrue(result["fail2ban"]["socket_present"])
        self.assertEqual(result["hints"], [])

    def test_missing_everything_reports_actionable_hints(self):
        result = collect(which=None, isdir=False, ismount=False, exists=False)

        self.assertFalse(result["ufw"]["binary_present"])
        self.assertFalse(result["ufw"]["config_dir_present"])
        self.assertFalse(result["fail2ban"]["socket_present"])
        hints = "\n".join(result["hints"])
        self.assertIn("ufw binary is missing", hints)
        self.assertIn("/etc/ufw", hints)
        self.assertIn("Fail2Ban socket", hints)

    def test_config_present_but_not_mounted_is_flagged(self):
        result = collect(ismount=False)

        self.assertTrue(result["ufw"]["config_dir_present"])
        self.assertFalse(result["ufw"]["config_dir_mounted"])
        self.assertIn("not a host bind mount", "\n".join(result["hints"]))

    def test_only_fail2ban_missing(self):
        result = collect(exists=False)

        self.assertEqual(len(result["hints"]), 1)
        self.assertIn("Fail2Ban", result["hints"][0])

    def test_diagnostics_do_not_expose_paths(self):
        result = collect(which="/usr/sbin/ufw")

        self.assertNotIn("/usr/sbin/ufw", str(result))


if __name__ == "__main__":
    unittest.main()
