"""Read-only diagnostics for the host UFW/Fail2Ban integration.

The dashboard can render an empty rule list for two very different reasons:
UFW has no rules, or the container cannot talk to the host firewall at all.
These checks are deliberately side-effect free and never execute a firewall
command, so they are safe to expose to an authenticated administrator.
"""

import os
import shutil
import stat

UFW_CONFIG_DIR = "/etc/ufw"
FAIL2BAN_SOCKET = "/var/run/fail2ban/fail2ban.sock"
PROC_STATUS = "/proc/self/status"


def _has_net_admin_capability() -> bool:
    """Inspect the current process capability mask without external commands."""
    try:
        with open(PROC_STATUS, encoding="ascii") as status_file:
            for line in status_file:
                if line.startswith("CapEff:"):
                    effective = int(line.split(":", maxsplit=1)[1].strip(), 16)
                    return bool(effective & (1 << 12))  # CAP_NET_ADMIN
    except (OSError, ValueError):
        return False
    return False


def _fail2ban_socket_path_accessible() -> bool:
    """Check the socket path type and permissions, not daemon liveness."""
    try:
        metadata = os.stat(FAIL2BAN_SOCKET, follow_symlinks=False)
        return stat.S_ISSOCK(metadata.st_mode) and os.access(
            FAIL2BAN_SOCKET, os.R_OK | os.W_OK, follow_symlinks=False
        )
    except OSError:
        return False


def collect_diagnostics() -> dict:
    """Return non-secret environment facts plus actionable hints."""
    ufw_binary_present = shutil.which("ufw") is not None
    config_dir_present = os.path.isdir(UFW_CONFIG_DIR)
    config_dir_mountpoint = os.path.ismount(UFW_CONFIG_DIR)
    net_admin_available = _has_net_admin_capability()
    fail2ban_socket_path_accessible = _fail2ban_socket_path_accessible()

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
    elif not config_dir_mountpoint:
        hints.append(
            (
                "ufw_config_not_mountpoint",
                (
                    "/etc/ufw exists in the container but is not a mount point. "
                    "Check the volume entry in docker-compose.yml."
                ),
            )
        )
    if not net_admin_available:
        hints.append(
            (
                "net_admin_missing",
                (
                    "The container process lacks NET_ADMIN. Add NET_ADMIN under cap_add "
                    "in docker-compose.yml and recreate the container."
                ),
            )
        )
    if not fail2ban_socket_path_accessible:
        hints.append(
            (
                "fail2ban_socket_missing",
                (
                    "The Fail2Ban socket is missing, is not a Unix socket, or is not "
                    "accessible. Mount '/var/run/fail2ban/fail2ban.sock' and check its "
                    "permissions."
                ),
            )
        )

    return {
        "ufw": {
            "binary_present": ufw_binary_present,
            "config_dir_present": config_dir_present,
            # A mountpoint can be a named volume; the app cannot prove its source.
            "config_dir_mountpoint": config_dir_mountpoint,
            "net_admin_available": net_admin_available,
        },
        "fail2ban": {
            # A filesystem check cannot prove that Fail2Ban is listening.
            "socket_path_accessible": fail2ban_socket_path_accessible,
        },
        # Codes are stable for UI translation; messages remain for API consumers.
        "hint_codes": [code for code, _message in hints],
        "hints": [message for _code, message in hints],
    }
