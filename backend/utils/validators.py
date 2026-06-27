"""
UFW-GUI - Validation and sanitization utilities
"""
import re


def is_valid_ip(ip: str) -> bool:
    if not ip:
        return True
    ipv4 = r"^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$"
    ipv6 = r"^[0-9a-fA-F:]+(\/\d{1,3})?$"
    return bool(re.match(ipv4, ip)) or bool(re.match(ipv6, ip))


def is_valid_port(port: str) -> bool:
    if not port:
        return True
    return bool(re.match(r"^\d+(:\d+)?$", port))


def is_valid_proto(proto: str) -> bool:
    if not proto:
        return True
    return proto.lower() in ["tcp", "udp"]


def is_valid_username(username: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_\-]+$", username))


def is_valid_jail(jail: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_\-]+$", jail))


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
