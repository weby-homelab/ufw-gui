"""First-admin setup requires a separate, non-disclosed bootstrap credential."""

import asyncio
import concurrent.futures
import os
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend import main
from backend.routers import auth_router
from backend.services import auth_service, database_service, filesystem_service


class SetupBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.database = self.root / "stats.db"
        audit_patch = patch.object(auth_router, "log_action")
        patches = (
            patch.object(filesystem_service, "DATA_DIR", str(self.root)),
            patch.object(
                filesystem_service, "USER_DATA_FILE", str(self.root / "users.json")
            ),
            patch.object(
                filesystem_service,
                "TEST_STATE_FILE",
                str(self.root / "test_state.json"),
            ),
            patch.object(database_service, "DATA_DIR", str(self.root)),
            patch.object(database_service, "DB_FILE", str(self.database)),
            audit_patch,
        )
        for item in patches:
            started = item.start()
            if item is audit_patch:
                self.audit = started
            self.addCleanup(item.stop)
        original = (
            main.app.state.storage_initialized,
            main.app.state.storage_initialization_attempted,
            main.app.state.storage_validated,
        )

        def restore_state():
            (
                main.app.state.storage_initialized,
                main.app.state.storage_initialization_attempted,
                main.app.state.storage_validated,
            ) = original

        self.addCleanup(restore_state)
        main.app.state.storage_initialized = False
        main.app.state.storage_initialization_attempted = False
        main.app.state.storage_validated = False
        database_service.initialize_empty_database()
        self.client = TestClient(
            main.app, base_url="https://testserver", raise_server_exceptions=False
        )
        self.setup_token = "fixture-only-setup-token-" + "x" * 32

    def setup(self, token=None, **values):
        payload = {"username": "operator", "password": "fixture-only-password"}
        payload.update(values)
        if token is not None:
            payload["setup_token"] = token
        return self.client.post("/api/auth/setup", json=payload)

    def test_unconfigured_or_short_token_refuses_without_reading_users_or_hashing(self):
        for configured in ("", "short", auth_service.SECRET_KEY, "☃" * 32, "x" * 257):
            with self.subTest(configured=bool(configured)):
                with (
                    patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": configured}),
                    patch.object(auth_router, "load_users") as load,
                    patch.object(auth_router, "hash_password") as hash_password,
                    patch.object(auth_router, "create_initial_admin") as create,
                ):
                    response = self.setup(self.setup_token)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(self.setup_token, response.text)
                load.assert_not_called()
                hash_password.assert_not_called()
                create.assert_not_called()
        self.audit.assert_not_called()

    def test_missing_or_wrong_token_is_forbidden_before_account_lookup(self):
        with patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": self.setup_token}):
            for supplied in (None, "wrong", "☃" * 32):
                with self.subTest(supplied_type=type(supplied).__name__):
                    with (
                        patch.object(auth_router, "load_users") as load,
                        patch.object(auth_router, "hash_password") as hash_password,
                        patch.object(auth_router, "create_initial_admin") as create,
                    ):
                        response = self.setup(supplied)
                    self.assertEqual(response.status_code, 403)
                    self.assertNotIn(self.setup_token, response.text)
                    load.assert_not_called()
                    hash_password.assert_not_called()
                    create.assert_not_called()
        self.audit.assert_not_called()

    def test_plain_http_and_spoofed_forwarded_proto_cannot_authorize_setup(self):
        client = TestClient(
            main.app, base_url="http://testserver", raise_server_exceptions=False
        )
        payload = {
            "username": "operator",
            "password": "fixture-only-password",
            "setup_token": self.setup_token,
        }
        with (
            patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": self.setup_token}),
            patch.object(auth_router, "load_users") as load,
            patch.object(auth_router, "hash_password") as hash_password,
        ):
            responses = (
                client.post("/api/auth/setup", json=payload),
                client.post(
                    "/api/auth/setup",
                    json=payload,
                    headers={"X-Forwarded-Proto": "https"},
                ),
            )
        self.assertEqual([response.status_code for response in responses], [403, 403])
        self.assertTrue(
            all(self.setup_token not in response.text for response in responses)
        )
        load.assert_not_called()
        hash_password.assert_not_called()
        self.audit.assert_not_called()

    def test_forwarded_https_is_used_only_from_a_configured_trusted_proxy(self):
        payload = {
            "username": "operator",
            "password": "fixture-only-password",
            "setup_token": self.setup_token,
        }
        with patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": self.setup_token}):
            untrusted = TestClient(
                ProxyHeadersMiddleware(main.app, trusted_hosts="127.0.0.1"),
                base_url="http://testserver",
                raise_server_exceptions=False,
            )
            response = untrusted.post(
                "/api/auth/setup", json=payload, headers={"X-Forwarded-Proto": "https"}
            )
            self.assertEqual(response.status_code, 403)
            trusted = TestClient(
                ProxyHeadersMiddleware(main.app, trusted_hosts="testclient"),
                base_url="http://testserver",
                raise_server_exceptions=False,
            )
            response = trusted.post(
                "/api/auth/setup", json=payload, headers={"X-Forwarded-Proto": "https"}
            )
            self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.setup_token, response.text)

    def test_valid_token_creates_one_admin_and_existing_login_needs_no_token(self):
        with patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": self.setup_token}):
            response = self.setup(self.setup_token)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(self.setup_token, response.text)
            self.assertEqual(
                self.setup(self.setup_token, username="second").status_code, 400
            )

        with patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": ""}):
            login = self.client.post(
                "/api/auth/login",
                data={"username": "operator", "password": "fixture-only-password"},
            )
        self.assertEqual(login.status_code, 200)
        access_token = login.json()["access_token"]
        self.assertEqual(
            auth_service.verify_access_token(access_token)["sub"], "operator"
        )
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(
                connection.execute("SELECT username, role FROM users").fetchall(),
                [("operator", "superadmin")],
            )

    def test_invalid_body_never_reflects_the_setup_token(self):
        with patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": self.setup_token}):
            responses = [
                self.setup(self.setup_token, username=[self.setup_token]),
                self.setup([self.setup_token]),
                self.setup(self.setup_token * 6),
            ]
        for response in responses:
            self.assertEqual(response.status_code, 422)
            self.assertNotIn(self.setup_token, response.text)
        self.audit.assert_not_called()

    def test_two_concurrent_valid_setup_requests_create_only_one_admin(self):
        hashing_started = threading.Barrier(2)

        def coordinated_hash(_password):
            hashing_started.wait(timeout=5)
            return "fixture-hash"

        def setup_user(username):
            try:
                asyncio.run(
                    auth_router.setup_admin(
                        request=Request(
                            {
                                "type": "http",
                                "scheme": "https",
                                "headers": [],
                                "path": "/api/auth/setup",
                                "server": ("testserver", 443),
                            }
                        ),
                        username=username,
                        password="fixture-only-password",
                        setup_token=self.setup_token,
                    )
                )
                return 200
            except HTTPException as exc:
                return exc.status_code

        with (
            patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": self.setup_token}),
            patch.object(auth_router, "hash_password", side_effect=coordinated_hash),
            concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool,
        ):
            results = list(pool.map(setup_user, ("operator1", "operator2")))

        self.assertEqual(sorted(results), [200, 400])
        with closing(sqlite3.connect(self.database)) as connection:
            rows = connection.execute("SELECT username, role FROM users").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn(rows[0][0], ("operator1", "operator2"))
        self.assertEqual(rows[0][1], "superadmin")

    def test_72_byte_multibyte_password_is_accepted(self):
        with patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": self.setup_token}):
            response = self.setup(self.setup_token, password="🚀" * 18)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.setup_token, response.text)

    def test_unacceptable_password_is_rejected_before_hashing(self):
        with (
            patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": self.setup_token}),
            patch.object(auth_router, "hash_password") as hash_password,
        ):
            for password in ("short", "a" * 73, "🚀" * 20):
                with self.subTest(password_length=len(password)):
                    response = self.setup(self.setup_token, password=password)
                    self.assertIn(response.status_code, (400, 422))
                    self.assertNotIn(self.setup_token, response.text)
            hash_password.assert_not_called()

    def test_unpaired_unicode_surrogate_in_password_is_rejected(self):
        body = (
            b'{"username":"operator","password":"\\ud800xxxxxxxxxxxx",'
            b'"setup_token":"' + self.setup_token.encode("ascii") + b'"}'
        )
        with (
            patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": self.setup_token}),
            patch.object(auth_router, "hash_password") as hash_password,
        ):
            response = self.client.post(
                "/api/auth/setup",
                content=body,
                headers={"Content-Type": "application/json"},
            )
        self.assertIn(response.status_code, (400, 422))
        self.assertNotIn(self.setup_token, response.text)
        hash_password.assert_not_called()

    def test_direct_setup_rejects_unpaired_surrogate_without_hashing(self):
        with (
            patch.dict(os.environ, {"UFW_GUI_SETUP_TOKEN": self.setup_token}),
            patch.object(auth_router, "hash_password") as hash_password,
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    auth_router.setup_admin(
                        request=Request(
                            {
                                "type": "http",
                                "scheme": "https",
                                "headers": [],
                                "path": "/api/auth/setup",
                                "server": ("testserver", 443),
                            }
                        ),
                        username="operator",
                        password="\ud800" + "x" * 12,
                        setup_token=self.setup_token,
                    )
                )
        self.assertEqual(raised.exception.status_code, 400)
        hash_password.assert_not_called()


if __name__ == "__main__":
    unittest.main()
