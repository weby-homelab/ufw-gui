"""Version source validation tests."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_versions import VersionConsistencyError, check_versions


def create_version_sources(root: Path, versions: dict[str, str]) -> None:
    (root / "backend").mkdir()
    (root / "frontend").mkdir()
    (root / "VERSION").write_text(versions["VERSION"] + "\n", encoding="utf-8")
    (root / "backend/main.py").write_text(
        "from fastapi import FastAPI\n"
        f'app = FastAPI(title="Test API", version="{versions["backend"]}")\n',
        encoding="utf-8",
    )
    package = {"name": "test-frontend", "version": versions["package"]}
    (root / "frontend/package.json").write_text(json.dumps(package), encoding="utf-8")
    lock = {
        "name": package["name"],
        "version": versions["lock"],
        "lockfileVersion": 3,
        "packages": {"": {"name": package["name"], "version": versions["lock"]}},
    }
    (root / "frontend/package-lock.json").write_text(json.dumps(lock), encoding="utf-8")


class VersionConsistencyTests(unittest.TestCase):
    def test_matching_version_sources_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_version_sources(
                root,
                {
                    "VERSION": "1.6.3",
                    "backend": "1.6.3",
                    "package": "1.6.3",
                    "lock": "1.6.3",
                },
            )

            self.assertEqual(check_versions(root), "1.6.3")

    def test_version_source_drift_fails_with_source_names(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_version_sources(
                root,
                {
                    "VERSION": "1.6.3",
                    "backend": "1.6.0",
                    "package": "1.6.2",
                    "lock": "1.6.2",
                },
            )

            with self.assertRaises(VersionConsistencyError) as raised:
                check_versions(root)

            self.assertIn("backend/main.py", str(raised.exception))
            self.assertIn("frontend/package.json", str(raised.exception))

    def test_non_release_semver_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_version_sources(
                root,
                {
                    "VERSION": "1.6.3-rc.1",
                    "backend": "1.6.3-rc.1",
                    "package": "1.6.3-rc.1",
                    "lock": "1.6.3-rc.1",
                },
            )

            with self.assertRaises(VersionConsistencyError):
                check_versions(root)


if __name__ == "__main__":
    unittest.main()
