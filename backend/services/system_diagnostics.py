"""Read-only diagnostics for the host UFW/Fail2Ban integration.

The dashboard can render an empty rule list for two very different reasons:
UFW has no rules, or the container cannot talk to the host firewall at all.
These checks are deliberately side-effect free and never execute a firewall
command, so they are safe to expose to an authenticated administrator.
"""

import os
import shutil

UFW_CONFIG_DIR = "/etc/ufw"
FAIL2BAN_SOCKET = "/var/run/fail2ban/fail2ban.sock"


def collect_diagnostics() -> dict:
    """Return non-secret environment facts plus actionable hints."""
    ufw_binary_present = shutil.which("ufw") is not None
    config_dir_present = os.path.isdir(UFW_CONFIG_DIR)
    config_dir_mounted = os.path.ismount(UFW_CONFIG_DIR)
    fail2ban_socket_present = os.path.exists(FAIL2BAN_SOCKET)

    hints: list[tuple[str, str]] = []
    if not ufw_binary_present:
        hints.append(
            (
                "ufw_binary_missing",
                (
                    "The ufw binary is missing from the container image; use an official image "
                    "built after 1.6.3 or rebuild from this repository."
                ),
            )
        )
    if not config_dir_present:
        hints.append(
            (
                "ufw_config_missing",
                (
                    "The host /etc/ufw directory is not mounted. Add the volume "
                    "'/etc/ufw:/etc/ufw' and restart the container."
                ),
            )
        )
    elif not config_dir_mounted:
        hints.append(
            (
                "ufw_config_not_mounted",
                (
                    "/etc/ufw exists in the container but is not a host bind mount. "
                    "Rules shown here may not match the host firewall."
                ),
            )
        )
    if not fail2ban_socket_present:
        hints.append(
            (
                "fail2ban_socket_missing",
                (
                    "The Fail2Ban socket is not mounted; Fail2Ban status will be unavailable. "
                    "Mount '/var/run/fail2ban/fail2ban.sock' to enable it."
                ),
            )
        )

    return {
        "ufw": {
            "binary_present": ufw_binary_present,
            "config_dir_present": config_dir_present,
            "config_dir_mounted": config_dir_mounted,
        },
        "fail2ban": {
            "socket_present": fail2ban_socket_present,
        },
        # Codes are stable for UI translation; messages remain for API consumers.
        "hint_codes": [code for code, _message in hints],
        "hints": [message for _code, message in hints],
    }
