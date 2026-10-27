"""Port and range validation boundaries must not change with lint cleanup."""

import unittest

from backend.utils.validators import is_valid_port


class PortValidationTests(unittest.TestCase):
    def test_valid_ports_and_ranges(self):
        for port in ("", "1", "65535", "1:65535", "80:80"):
            with self.subTest(port=port):
                self.assertTrue(is_valid_port(port))

    def test_invalid_ports_and_ranges(self):
        for port in ("0", "65536", "9:8", "1:65536", "abc", "1:2:3"):
            with self.subTest(port=port):
                self.assertFalse(is_valid_port(port))
