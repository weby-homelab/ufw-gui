"""Read-only diagnostics for the host UFW/Fail2Ban integration."""

import io
import os
import socket
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.services import system_diagnostics


def collect(
    which="/usr/sbin/ufw",
    isdir=True,
    ismount=True,
    net_admin=True,
    socket_path_accessible=True,
):
    with (
        patch.object(system_diagnostics.shutil, "which", return_value=which),
        patch.object(system_diagnostics.os.path, "isdir", return_value=isdir),
        patch.object(system_diagnostics.os.path, "ismount", return_value=ismount),
        patch.object(
            system_diagnostics, "_has_net_admin_capability", return_value=net_admin
        ),
        patch.object(
            system_diagnostics,
            "_fail2ban_socket_path_accessible",
            return_value=socket_path_accessible,
        ),
    ):
        return system_diagnostics.collect_diagnostics()


class SystemDiagnosticsTests(unittest.TestCase):
    def test_healthy_integration_has_no_hints(self):
        result = collect()

        self.assertTrue(result["ufw"]["binary_present"])
        self.assertTrue(result["ufw"]["config_dir_present"])
        self.assertTrue(result["ufw"]["config_dir_mountpoint"])
        self.assertTrue(result["ufw"]["net_admin_available"])
        self.assertTrue(result["fail2ban"]["socket_path_accessible"])
        self.assertEqual(result["hints"], [])
        self.assertEqual(result["hint_codes"], [])

    def test_missing_integration_prerequisites_report_stable_codes(self):
        result = collect(
            which=None,
            isdir=False,
            ismount=False,
            net_admin=False,
            socket_path_accessible=False,
        )

        self.assertFalse(result["ufw"]["binary_present"])
        self.assertFalse(result["ufw"]["config_dir_present"])
        self.assertFalse(result["ufw"]["net_admin_available"])
        self.assertFalse(result["fail2ban"]["socket_path_accessible"])
        self.assertEqual(
            result["hint_codes"],
            [
                "ufw_binary_missing",
                "ufw_config_missing",
                "net_admin_missing",
                "fail2ban_socket_missing",
            ],
        )
        hints = "\n".join(result["hints"])
        self.assertIn("ufw binary is missing", hints)
        self.assertIn("/etc/ufw", hints)
        self.assertIn("NET_ADMIN", hints)
        self.assertIn("Fail2Ban socket", hints)

    def test_config_directory_without_mountpoint_is_flagged(self):
        result = collect(ismount=False)

        self.assertTrue(result["ufw"]["config_dir_present"])
        self.assertFalse(result["ufw"]["config_dir_mountpoint"])
        self.assertIn("ufw_config_not_mountpoint", result["hint_codes"])

    def test_diagnostics_do_not_claim_to_verify_mount_source(self):
        result = collect(ismount=True)

        self.assertNotIn("config_dir_mounted", result["ufw"])
        self.assertNotIn("bind mount", "\n".join(result["hints"]))

    def test_capability_mask_checks_net_admin_bit(self):
        mask = 1 << 12
        with patch(
            "builtins.open", return_value=io.StringIO(f"CapEff:\t{mask:016x}\n")
        ):
            self.assertTrue(system_diagnostics._has_net_admin_capability())
        with patch(
            "builtins.open", return_value=io.StringIO("CapEff:\t0000000000000000\n")
        ):
            self.assertFalse(system_diagnostics._has_net_admin_capability())

    def test_fail2ban_path_check_does_not_claim_daemon_liveness(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "fail2ban.sock")
            with patch.object(system_diagnostics, "FAIL2BAN_SOCKET", path):
                with open(path, "w", encoding="ascii") as regular_file:
                    regular_file.write("not a socket")
                self.assertFalse(system_diagnostics._fail2ban_socket_path_accessible())

                os.remove(path)
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    server.bind(path)
                    # This bound socket is intentionally not listening. The
                    # diagnostic reports path accessibility, not daemon health.
                    self.assertTrue(
                        system_diagnostics._fail2ban_socket_path_accessible()
                    )
                finally:
                    server.close()

    def test_diagnostics_do_not_expose_paths(self):
        result = collect(which="/usr/sbin/ufw")

        self.assertNotIn("/usr/sbin/ufw", str(result))


if __name__ == "__main__":
    unittest.main()
