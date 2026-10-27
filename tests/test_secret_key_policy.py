"""JWT signing must fail at startup for missing or undersized keys."""

import os
import subprocess
import sys
import unittest


class SecretKeyPolicyTests(unittest.TestCase):
    def import_auth_with_key(self, value):
        environment = os.environ.copy()
        if value is None:
            environment.pop("UFW_GUI_SECRET_KEY", None)
        else:
            environment["UFW_GUI_SECRET_KEY"] = value
        return subprocess.run(
            [sys.executable, "-c", "import backend.services.auth_service"],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

    def test_missing_and_short_keys_are_rejected_without_echoing_them(self):
        for key in (None, "", "fixture-short-key", "a" * 31):
            with self.subTest(length=None if key is None else len(key)):
                result = self.import_auth_with_key(key)
                self.assertNotEqual(result.returncode, 0)
                if key:
                    self.assertNotIn(key, result.stderr)

    def test_a_key_of_at_least_32_bytes_is_accepted(self):
        result = self.import_auth_with_key("fixture-key-" + "x" * 32)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
