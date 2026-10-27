"""The image listens on loopback unless an operator explicitly opts in otherwise."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class ImageStartCommandTests(unittest.TestCase):
    def run_start_command(self, extra_environment=None):
        dockerfile = Path(__file__).resolve().parent.parent / "Dockerfile"
        commands = [
            line[4:]
            for line in dockerfile.read_text().splitlines()
            if line.startswith("CMD ")
        ]
        self.assertEqual(len(commands), 1)
        command = json.loads(commands[0])
        self.assertEqual(command[:2], ["sh", "-c"])
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "uvicorn"
            fake.write_text('#!/usr/bin/sh\nprintf "%s\\n" "$@"\n')
            fake.chmod(0o755)
            environment = {"PATH": directory + ":/usr/bin", "HOME": directory}
            environment.update(extra_environment or {})
            result = subprocess.run(
                ["/usr/bin/sh", "-c", command[2]],
                env=environment,
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
        return result.stdout.splitlines()

    def test_default_listener_is_loopback(self):
        self.assertEqual(
            self.run_start_command(),
            ["backend.main:app", "--host", "127.0.0.1", "--port", "8080"],
        )

    def test_explicit_listener_and_port_are_single_quoted_arguments(self):
        self.assertEqual(
            self.run_start_command(
                {"UFW_GUI_BIND_ADDRESS": "127.0.0.2;not-a-command", "PORT": "18081"}
            ),
            [
                "backend.main:app",
                "--host",
                "127.0.0.2;not-a-command",
                "--port",
                "18081",
            ],
        )


if __name__ == "__main__":
    unittest.main()
