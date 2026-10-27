"""Validators and HTTP routes reject unsafe command and identity inputs."""

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend import main
from backend.routers import admin_router, fail2ban_router, ufw_router
from backend.services import auth_service, database_service, filesystem_service
from backend.utils.validators import is_valid_jail, is_valid_port, is_valid_username


class ValidatorBoundaryTests(unittest.TestCase):
    def test_port_rejects_newline_unicode_and_oversized_digits(self):
        self.assertFalse(is_valid_port("22\n"))
        self.assertFalse(is_valid_port("٢٢"))
        self.assertFalse(is_valid_port("9" * 5000))

    def test_username_rejects_trailing_newline(self):
        self.assertFalse(is_valid_username("operator\n"))

    def test_jail_rejects_trailing_newline(self):
        self.assertFalse(is_valid_jail("sshd\n"))

    def test_http_routes_reject_invalid_input_without_command_or_user_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stats.db")
            marker_path = os.path.join(directory, "test_state.json")
            user_data_path = os.path.join(directory, "users.json")
            with (
                patch.object(filesystem_service, "DATA_DIR", directory),
                patch.object(filesystem_service, "USER_DATA_FILE", user_data_path),
                patch.object(filesystem_service, "TEST_STATE_FILE", marker_path),
                patch.object(database_service, "DATA_DIR", directory),
                patch.object(database_service, "DB_FILE", database_path),
            ):
                database_service.initialize_empty_database()
                with closing(sqlite3.connect(database_path)) as connection, connection:
                    connection.execute(
                        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                        ("operator", "test-password-hash", "superadmin"),
                    )

                original_initialized = main.app.state.storage_initialized
                original_validated = main.app.state.storage_validated
                original_attempted = main.app.state.storage_initialization_attempted
                main.app.state.storage_initialized = False
                main.app.state.storage_validated = False
                main.app.state.storage_initialization_attempted = False
                token = auth_service.create_access_token("operator", "superadmin")
                headers = {"Authorization": f"Bearer {token}"}
                try:
                    with (
                        patch.object(
                            ufw_router, "run_ufw", new_callable=AsyncMock
                        ) as run_ufw,
                        patch.object(
                            fail2ban_router, "run_fail2ban", new_callable=AsyncMock
                        ) as run_fail2ban,
                        patch.object(admin_router, "hash_password") as hash_password,
                        patch.object(
                            admin_router, "create_regular_user"
                        ) as create_user,
                        patch.object(ufw_router, "log_action") as ufw_log_action,
                        patch.object(
                            fail2ban_router, "log_action"
                        ) as fail2ban_log_action,
                        patch.object(admin_router, "log_action") as admin_log_action,
                    ):
                        run_ufw.return_value = "mocked"
                        run_fail2ban.return_value = "mocked"
                        client = TestClient(main.app, raise_server_exceptions=False)
                        responses = [
                            client.post(
                                "/api/rule",
                                json={
                                    "action": "allow",
                                    "port": "22\n",
                                    "proto": "",
                                    "ip": "",
                                },
                                headers=headers,
                            ),
                            client.post(
                                "/api/rule",
                                json={
                                    "action": "allow",
                                    "port": "٢٢",
                                    "proto": "",
                                    "ip": "",
                                },
                                headers=headers,
                            ),
                            client.post(
                                "/api/rule",
                                json={
                                    "action": "allow",
                                    "port": "9" * 5000,
                                    "proto": "",
                                    "ip": "",
                                },
                                headers=headers,
                            ),
                            client.post(
                                "/api/fail2ban/unban",
                                json={"ip": "192.0.2.1", "jail": "sshd\n"},
                                headers=headers,
                            ),
                            client.post(
                                "/api/users",
                                json={"username": "new-user\n", "password": "test"},
                                headers=headers,
                            ),
                        ]

                    self.assertEqual(
                        [response.status_code for response in responses],
                        [400, 400, 400, 400, 400],
                    )
                    self.assertEqual(
                        [response.json()["detail"] for response in responses],
                        [
                            "Invalid Port format",
                            "Invalid Port format",
                            "Invalid Port format",
                            "Invalid Jail",
                            "Invalid username",
                        ],
                    )
                    run_ufw.assert_not_awaited()
                    run_fail2ban.assert_not_awaited()
                    hash_password.assert_not_called()
                    create_user.assert_not_called()
                    ufw_log_action.assert_not_called()
                    fail2ban_log_action.assert_not_called()
                    admin_log_action.assert_not_called()
                    with closing(sqlite3.connect(database_path)) as connection:
                        self.assertEqual(
                            connection.execute("SELECT username FROM users").fetchall(),
                            [("operator",)],
                        )
                    self.assertFalse(os.path.exists(user_data_path))
                finally:
                    main.app.state.storage_initialized = original_initialized
                    main.app.state.storage_validated = original_validated
                    main.app.state.storage_initialization_attempted = original_attempted


if __name__ == "__main__":
    unittest.main()
