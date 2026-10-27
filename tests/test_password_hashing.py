"""Direct bcrypt hashing regression tests (issue #45)."""

import os
import sys
import unittest

import bcrypt

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.services import auth_service


class PasswordHashingTests(unittest.TestCase):
    def test_hash_and_verify_roundtrip(self):
        hashed = auth_service.hash_password("correct horse battery staple")

        self.assertTrue(hashed.startswith("$2b$12$"))
        self.assertTrue(
            auth_service.verify_password("correct horse battery staple", hashed)
        )
        self.assertFalse(auth_service.verify_password("wrong password", hashed))

    def test_hashes_are_salted(self):
        first = auth_service.hash_password("same password twice")
        second = auth_service.hash_password("same password twice")

        self.assertNotEqual(first, second)
        self.assertTrue(auth_service.verify_password("same password twice", first))
        self.assertTrue(auth_service.verify_password("same password twice", second))

    def test_legacy_passlib_bcrypt_hash_remains_verifiable(self):
        # passlib emitted standard bcrypt hashes; existing users must keep working.
        legacy = bcrypt.hashpw(b"legacy-password", bcrypt.gensalt(rounds=12)).decode(
            "ascii"
        )

        self.assertTrue(auth_service.verify_password("legacy-password", legacy))

    def test_unicode_password_roundtrip(self):
        password = "пароль-з-кирилицею-12"
        hashed = auth_service.hash_password(password)

        self.assertTrue(auth_service.verify_password(password, hashed))

    def test_password_over_72_bytes_is_rejected_not_truncated(self):
        with self.assertRaises(ValueError):
            auth_service.hash_password("a" * 73)

    def test_surrogate_encoding_is_rejected(self):
        with self.assertRaises(ValueError):
            auth_service.hash_password("\ud800" * 13)

    def test_malformed_or_non_ascii_hash_fails_closed(self):
        for hashed in ("", "not-a-hash", "$2b$12$", "\ud800"):
            with self.subTest(hashed=repr(hashed)):
                self.assertFalse(auth_service.verify_password("password", hashed))
        self.assertFalse(auth_service.verify_password("password", None))  # type: ignore[arg-type]

    def test_passlib_layer_is_not_used(self):
        self.assertFalse(hasattr(auth_service, "pwd_context"))
        self.assertNotIn("passlib", sys.modules)


if __name__ == "__main__":
    unittest.main()
