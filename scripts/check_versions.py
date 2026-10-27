"""Verify that every release artifact uses the canonical project version."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

VERSION_PATTERN = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class VersionConsistencyError(ValueError):
    """Raised when a version source is missing, invalid, or inconsistent."""


def _backend_api_version(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise VersionConsistencyError("cannot parse backend/main.py") from exc

    versions = [
        keyword.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "FastAPI"
        for keyword in node.keywords
        if keyword.arg == "version"
        and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
    ]
    if len(versions) != 1:
        raise VersionConsistencyError(
            "backend/main.py must define exactly one literal FastAPI version"
        )
    return versions[0]


def _version_sources(root: Path) -> dict[str, str]:
    try:
        frontend = json.loads(
            (root / "frontend/package.json").read_text(encoding="utf-8")
        )
        lockfile = json.loads(
            (root / "frontend/package-lock.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise VersionConsistencyError(
            "frontend package metadata is missing or invalid"
        ) from exc

    try:
        lock_root_version = lockfile["packages"][""]["version"]
    except (KeyError, TypeError) as exc:
        raise VersionConsistencyError(
            "frontend/package-lock.json is missing packages[''].version"
        ) from exc

    return {
        "VERSION": (root / "VERSION").read_text(encoding="utf-8").strip(),
        "frontend/package.json": frontend.get("version", ""),
        "frontend/package-lock.json": lockfile.get("version", ""),
        "frontend/package-lock.json packages['']": lock_root_version,
        "backend/main.py": _backend_api_version(root / "backend/main.py"),
    }


def check_versions(root: Path | str = PROJECT_ROOT) -> str:
    """Return the canonical version or raise with all inconsistent sources."""
    root_path = Path(root)
    try:
        sources = _version_sources(root_path)
    except OSError as exc:
        raise VersionConsistencyError(
            "a release version source is missing or unreadable"
        ) from exc

    invalid = [
        name
        for name, value in sources.items()
        if not isinstance(value, str) or not VERSION_PATTERN.fullmatch(value)
    ]
    if invalid:
        raise VersionConsistencyError(
            "invalid MAJOR.MINOR.PATCH version in: " + ", ".join(invalid)
        )

    canonical = sources["VERSION"]
    mismatched = [
        f"{name}={value}" for name, value in sources.items() if value != canonical
    ]
    if mismatched:
        raise VersionConsistencyError(
            f"VERSION={canonical} does not match " + ", ".join(mismatched)
        )
    return canonical


def main() -> int:
    try:
        version = check_versions()
    except VersionConsistencyError as exc:
        print(f"Version consistency check failed: {exc}", file=sys.stderr)
        return 1
    print(f"Version sources agree: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
