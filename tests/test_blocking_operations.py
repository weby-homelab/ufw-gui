"""Mutation locks remain held until side-effecting worker threads finish."""

import asyncio
import fcntl
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import closing
from unittest.mock import patch

os.environ.setdefault("UFW_GUI_SECRET_KEY", "test-only-secret-key-at-least-32-bytes")

from backend.routers import ufw_router
from backend.services import (
    database_service,
    filesystem_service,
    recovery_guard,
    subprocess_service,
)
from backend.services.async_operations import run_to_thread_to_completion


def create_test_database(directory):
    with closing(sqlite3.connect(os.path.join(directory, "stats.db"))) as database:
        database.executescript(
            "CREATE TABLE drops (id INTEGER PRIMARY KEY, ts TIMESTAMP, src TEXT, "
            "proto TEXT, port TEXT, UNIQUE(ts, src, port));"
            "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, ts TIMESTAMP, "
            "username TEXT, action TEXT, details TEXT);"
            "CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, role TEXT);"
        )
    with patch.object(database_service, "DB_FILE", os.path.join(directory, "stats.db")):
        database_service.init_db()


class BlockingOperationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancellation_waits_for_worker_before_propagating(self):
        started = threading.Event()
        release = threading.Event()

        def blocking_operation():
            started.set()
            release.wait(timeout=2)
            return "finished"

        task = asyncio.create_task(run_to_thread_to_completion(blocking_operation))
        self.assertTrue(await asyncio.to_thread(started.wait, 1))
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())

        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_loop_shutdown_cancellation_does_not_cancel_worker_future(self):
        started = threading.Event()
        release = threading.Event()
        finished = threading.Event()

        def blocking_operation():
            started.set()
            release.wait(timeout=2)
            finished.set()

        async def cancel_all_tasks_like_loop_shutdown():
            asyncio.create_task(run_to_thread_to_completion(blocking_operation))
            self.assertTrue(await asyncio.to_thread(started.wait, 1))
            current = asyncio.current_task()
            pending = [task for task in asyncio.all_tasks() if task is not current]
            for task in pending:
                task.cancel()
            timer = threading.Timer(0.1, release.set)
            timer.start()
            try:
                await asyncio.gather(*pending, return_exceptions=True)
                self.assertTrue(finished.is_set())
            finally:
                release.set()
                timer.join(timeout=1)

        await asyncio.wait_for(cancel_all_tasks_like_loop_shutdown(), timeout=2)

    async def test_route_keeps_interprocess_lock_until_subprocess_thread_finishes(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "test_state.json")
            started = threading.Event()
            release = threading.Event()
            calls = 0

            def blocking_subprocess(*args, **kwargs):
                nonlocal calls
                calls += 1
                self.assertEqual(len(kwargs.get("pass_fds", ())), 1)
                if calls == 1:
                    started.set()
                    release.wait(timeout=2)
                return subprocess.CompletedProcess(args[0], 0, stdout="ok", stderr="")

            with (
                patch.object(filesystem_service, "TEST_STATE_FILE", marker),
                patch.object(
                    subprocess_service, "run", side_effect=blocking_subprocess
                ),
                patch.object(ufw_router, "log_action"),
            ):
                first = asyncio.create_task(
                    ufw_router.reload_firewall(user={"username": "admin"})
                )
                self.assertTrue(await asyncio.to_thread(started.wait, 1))
                first.cancel()
                await asyncio.sleep(0)
                self.assertFalse(first.done())

                lock_waiting = asyncio.Event()
                original_try_acquire = recovery_guard._try_acquire_mutation_lock

                def observe_lock_wait():
                    descriptor = original_try_acquire()
                    if descriptor is None:
                        lock_waiting.set()
                    return descriptor

                with patch.object(
                    recovery_guard,
                    "_try_acquire_mutation_lock",
                    side_effect=observe_lock_wait,
                ):
                    second = asyncio.create_task(
                        ufw_router.reload_firewall(user={"username": "admin"})
                    )
                    await asyncio.wait_for(lock_waiting.wait(), timeout=1)
                    self.assertFalse(second.done())
                    self.assertEqual(calls, 1)

                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await first
                result = await asyncio.wait_for(second, timeout=1)

            self.assertEqual(result, {"result": "ok"})
            self.assertEqual(calls, 2)

    def test_firewall_subprocess_keeps_directory_lock_after_app_process_death(self):
        with tempfile.TemporaryDirectory() as directory:
            create_test_database(directory)
            marker = os.path.join(directory, "test_state.json")
            ready = os.path.join(directory, "subprocess-started")
            runner = os.path.join(directory, "locked_parent.py")
            child_code = (
                f"import pathlib,time; pathlib.Path({ready!r}).write_text('ready'); "
                "time.sleep(0.8)"
            )
            with open(runner, "w", encoding="utf-8") as output:
                output.write(
                    "import asyncio, os, sys\n"
                    f"sys.path.insert(0, {os.path.dirname(os.path.dirname(__file__))!r})\n"
                    "from backend.services import filesystem_service\n"
                    "from backend.services import database_service\n"
                    "from backend.services import subprocess_service\n"
                    "from backend.services.recovery_guard import firewall_mutation_guard\n"
                    f"filesystem_service.TEST_STATE_FILE = {marker!r}\n"
                    f"database_service.DB_FILE = {os.path.join(directory, 'stats.db')!r}\n"
                    "database_service.init_db()\n"
                    "async def main():\n"
                    "    async with firewall_mutation_guard():\n"
                    f"        await subprocess_service._run_command([sys.executable, '-c', {child_code!r}])\n"
                    "asyncio.run(main())\n"
                )

            with patch.object(filesystem_service, "TEST_STATE_FILE", marker):
                holder = subprocess.Popen(
                    [sys.executable, runner],
                    cwd=os.path.dirname(os.path.dirname(__file__)),
                    env=os.environ.copy(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                acquired = None
                try:
                    deadline = time.monotonic() + 3
                    while not os.path.exists(ready) and holder.poll() is None:
                        if time.monotonic() >= deadline:
                            self.fail("subprocess did not start before the deadline")
                        time.sleep(0.01)
                    self.assertTrue(os.path.exists(ready))

                    holder.kill()
                    holder.wait(timeout=2)

                    immediate = recovery_guard._try_acquire_mutation_lock()
                    if immediate is not None:
                        fcntl.flock(immediate[0], fcntl.LOCK_UN)
                        os.close(immediate[1])
                        os.close(immediate[0])
                    self.assertIsNone(
                        immediate,
                        "the firewall child must retain the lock after its app parent dies",
                    )

                    deadline = time.monotonic() + 3
                    while acquired is None and time.monotonic() < deadline:
                        acquired = recovery_guard._try_acquire_mutation_lock()
                        if acquired is None:
                            time.sleep(0.02)
                    self.assertIsNotNone(
                        acquired, "lock should release after child exit"
                    )
                finally:
                    if holder.poll() is None:
                        holder.kill()
                        holder.wait(timeout=2)
                    if acquired is not None:
                        fcntl.flock(acquired[0], fcntl.LOCK_UN)
                        os.close(acquired[1])
                        os.close(acquired[0])


if __name__ == "__main__":
    unittest.main()
