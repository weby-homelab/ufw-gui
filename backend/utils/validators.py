"""
UFW-GUI - Validation and sanitization utilities
"""

import ipaddress
import re


def is_valid_ip(ip: str) -> bool:
    if not ip:
        return True
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        try:
            ipaddress.ip_network(ip, strict=False)
            return True
        except ValueError:
            return False


def is_valid_port(port: str) -> bool:
    if not port:
        return True
    if not re.fullmatch(r"[0-9]+(:[0-9]+)?", port):
        return False
    parts = port.split(":")
    try:
        values = [int(part) for part in parts]
    except ValueError:
        return False
    if any(value < 1 or value > 65535 for value in values):
        return False
    return len(values) != 2 or values[0] <= values[1]


def is_valid_proto(proto: str) -> bool:
    if not proto:
        return True
    return proto.lower() in ["tcp", "udp"]


def is_valid_username(username: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z0-9_-]+", username))


def is_valid_jail(jail: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z0-9_-]+", jail))


def is_valid_new_password(password: str) -> bool:
    """Bound new bcrypt passwords without changing verification of legacy users."""
    if not 12 <= len(password) <= 72:
        return False
    try:
        return len(password.encode("utf-8")) <= 72
    except UnicodeEncodeError:
        return False


def validate_args(args) -> list:
    safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.:/"
    safe_args = []
    for arg in args:
        str_arg = str(arg)
        for ch in str_arg:
            if ch not in safe_chars:
                raise ValueError(f"Invalid characters in command argument: {arg}")
        safe_arg = "".join(safe_chars[safe_chars.index(ch)] for ch in str_arg)
        safe_args.append(safe_arg)
    return safe_args


def sanitize_label(label: str) -> str:
    return "".join([c if c.isalnum() else "_" for c in label])


def sanitize_snapshot_name(name: str) -> str:
    return "".join([c if c.isalnum() or c == "_" else "_" for c in name])
