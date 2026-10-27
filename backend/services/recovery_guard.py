"""Inter-process serialization and fail-closed guard for firewall mutations."""

import asyncio
import contextvars
import fcntl
import logging
import os
import stat
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from fastapi import HTTPException

from backend.services import database_service, filesystem_service

logger = logging.getLogger(__name__)

MANUAL_RECOVERY_REQUIRED = (
    "manual_recovery_required: a previous firewall test state is unresolved; "
    "automatic rollback is disabled and firewall mutations are blocked."
)
RECOVERY_STATE_UNAVAILABLE = (
    "manual_recovery_required: recovery state storage is unavailable or unsafe; "
    "firewall mutations are blocked."
)
LOCK_TIMEOUT = (
    "firewall_mutation_lock_timeout: another firewall operation is still running."
)
LOCK_TIMEOUT_SECONDS = 30.0
LOCK_RETRY_SECONDS = 0.05
P = ParamSpec("P")
R = TypeVar("R")
_MUTATION_LOCK_DESCRIPTOR: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "firewall_mutation_lock_descriptor", default=None
)
_MUTATION_LOCK_OWNER: contextvars.ContextVar[asyncio.Task[Any] | None] = (
    contextvars.ContextVar("firewall_mutation_lock_owner", default=None)
)
_MUTATION_DATABASE_DESCRIPTOR: contextvars.ContextVar[int | None] = (
    contextvars.ContextVar("firewall_mutation_database_descriptor", default=None)
)


def mutation_lock_descriptors() -> tuple[int, int] | None:
    """Return active storage descriptors owned by the current mutation task."""
    descriptor = _MUTATION_LOCK_DESCRIPTOR.get()
    database_descriptor = _MUTATION_DATABASE_DESCRIPTOR.get()
    if (
        descriptor is None
        or database_descriptor is None
        or _MUTATION_LOCK_OWNER.get() is not asyncio.current_task()
    ):
        return None
    return descriptor, database_descriptor


def _assert_recovery_directory_identity(descriptor: int) -> None:
    data_dir = os.path.dirname(os.path.abspath(filesystem_service.TEST_STATE_FILE))
    descriptor_metadata = os.fstat(descriptor)
    path_metadata = os.stat(data_dir, follow_symlinks=False)
    if (
        not stat.S_ISDIR(descriptor_metadata.st_mode)
        or descriptor_metadata.st_mode & 0o022
        or not stat.S_ISDIR(path_metadata.st_mode)
        or path_metadata.st_mode & 0o022
        or (descriptor_metadata.st_dev, descriptor_metadata.st_ino)
        != (path_metadata.st_dev, path_metadata.st_ino)
    ):
        raise PermissionError("Recovery directory changed while its lock was held")
    trusted_identity = database_service.trusted_storage_identity(data_dir)
    if (
        trusted_identity is None
        or (
            path_metadata.st_dev,
            path_metadata.st_ino,
        )
        != trusted_identity[:2]
    ):
        raise PermissionError(
            "Recovery directory differs from startup-validated storage"
        )


def _assert_recovery_database_identity(
    directory_descriptor: int,
    database_descriptor: int,
) -> None:
    data_dir = os.path.dirname(os.path.abspath(filesystem_service.TEST_STATE_FILE))
    entry_metadata = os.stat(
        "stats.db", dir_fd=directory_descriptor, follow_symlinks=False
    )
    database_metadata = os.fstat(database_descriptor)
    if (
        not stat.S_ISREG(database_metadata.st_mode)
        or database_metadata.st_mode & 0o022
        or (
            entry_metadata.st_dev,
            entry_metadata.st_ino,
        )
        != (database_metadata.st_dev, database_metadata.st_ino)
    ):
        raise PermissionError(
            "Application database changed while recovery lock was held"
        )
    trusted_identity = database_service.trusted_storage_identity(data_dir)
    if (
        trusted_identity is None
        or (
            database_metadata.st_dev,
            database_metadata.st_ino,
        )
        != trusted_identity[2:]
    ):
        raise PermissionError(
            "Application database differs from startup-validated storage"
        )


def ensure_recovery_directory_stable() -> None:
    """Fail closed if the locked directory no longer backs the recovery path."""
    descriptor = _MUTATION_LOCK_DESCRIPTOR.get()
    owner = _MUTATION_LOCK_OWNER.get()
    if descriptor is None and owner is None:
        return
    if descriptor is None or owner is not asyncio.current_task():
        logger.error("Firewall subprocess requested outside its owning mutation task.")
        raise HTTPException(status_code=503, detail=RECOVERY_STATE_UNAVAILABLE)

    try:
        _assert_recovery_directory_identity(descriptor)
        database_descriptor = _MUTATION_DATABASE_DESCRIPTOR.get()
        if database_descriptor is None:
            raise PermissionError("Application database identity is unavailable")
        _assert_recovery_database_identity(descriptor, database_descriptor)
    except OSError as exc:
        logger.error(
            "Recovery directory identity check failed (%s).", type(exc).__name__
        )
        raise HTTPException(status_code=503, detail=RECOVERY_STATE_UNAVAILABLE) from exc


def ensure_firewall_mutation_admitted() -> None:
    """Recheck storage and marker immediately before launching a firewall command."""
    ensure_recovery_directory_stable()
    descriptor = _MUTATION_LOCK_DESCRIPTOR.get()
    owner = _MUTATION_LOCK_OWNER.get()
    if descriptor is None and owner is None:
        return
    if descriptor is None or owner is not asyncio.current_task():
        raise HTTPException(status_code=503, detail=RECOVERY_STATE_UNAVAILABLE)
    database_descriptor = _MUTATION_DATABASE_DESCRIPTOR.get()
    if database_descriptor is None:
        raise HTTPException(status_code=503, detail=RECOVERY_STATE_UNAVAILABLE)
    if filesystem_service.has_unresolved_test_marker(
        directory_fd=descriptor,
        database_fd=database_descriptor,
        database_validated=True,
    ):
        raise HTTPException(status_code=503, detail=MANUAL_RECOVERY_REQUIRED)
    # Recheck directory and database identity after the marker lookup, directly
    # before handing control to the subprocess launcher.
    ensure_recovery_directory_stable()


def ensure_firewall_subprocess_admitted(
    directory_descriptor: int,
    database_descriptor: int,
) -> None:
    """Perform the final marker/storage check synchronously in the worker thread."""
    try:
        _assert_recovery_directory_identity(directory_descriptor)
        _assert_recovery_database_identity(directory_descriptor, database_descriptor)
        if filesystem_service.has_unresolved_test_marker(
            directory_fd=directory_descriptor,
            database_fd=database_descriptor,
            database_validated=False,
        ):
            raise HTTPException(status_code=503, detail=MANUAL_RECOVERY_REQUIRED)
        _assert_recovery_directory_identity(directory_descriptor)
        _assert_recovery_database_identity(directory_descriptor, database_descriptor)
    except OSError as exc:
        logger.error(
            "Recovery storage changed before firewall subprocess (%s).",
            type(exc).__name__,
        )
        raise HTTPException(status_code=503, detail=RECOVERY_STATE_UNAVAILABLE) from exc


def has_unresolved_recovery_marker() -> bool:
    """Inspect marker and database through the directory inode protected by flock."""
    ensure_recovery_directory_stable()
    descriptor = _MUTATION_LOCK_DESCRIPTOR.get()
    owner = _MUTATION_LOCK_OWNER.get()
    if descriptor is None and owner is None:
        return filesystem_service.has_unresolved_test_marker()
    if descriptor is None or owner is not asyncio.current_task():
        raise HTTPException(status_code=503, detail=RECOVERY_STATE_UNAVAILABLE)
    database_descriptor = _MUTATION_DATABASE_DESCRIPTOR.get()
    if database_descriptor is None:
        raise HTTPException(status_code=503, detail=RECOVERY_STATE_UNAVAILABLE)
    return filesystem_service.has_unresolved_test_marker(
        directory_fd=descriptor,
        database_fd=database_descriptor,
        database_validated=True,
    )


def _try_acquire_mutation_lock() -> tuple[int, int] | None:
    data_dir = os.path.dirname(os.path.abspath(filesystem_service.TEST_STATE_FILE))
    descriptor = os.open(
        data_dir,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    keep_descriptor = False
    database_descriptor = None
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_mode & 0o022:
            raise PermissionError("Unsafe firewall mutation lock directory")

        path_metadata = os.stat(data_dir, follow_symlinks=False)
        if (metadata.st_dev, metadata.st_ino) != (
            path_metadata.st_dev,
            path_metadata.st_ino,
        ):
            raise PermissionError("Firewall mutation lock directory changed")

        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return None

        database_entry = os.stat("stats.db", dir_fd=descriptor, follow_symlinks=False)
        if not stat.S_ISREG(database_entry.st_mode):
            raise PermissionError("Unsafe persistent application database")
        database_descriptor = os.open(
            "stats.db",
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=descriptor,
        )
        database_metadata = os.fstat(database_descriptor)
        current_database_entry = os.stat(
            "stats.db", dir_fd=descriptor, follow_symlinks=False
        )
        if (database_metadata.st_dev, database_metadata.st_ino) != (
            database_entry.st_dev,
            database_entry.st_ino,
        ) or (database_metadata.st_dev, database_metadata.st_ino) != (
            current_database_entry.st_dev,
            current_database_entry.st_ino,
        ):
            raise PermissionError("Persistent application database changed")

        trusted_identity = database_service.trusted_storage_identity(data_dir)
        actual_identity = (
            metadata.st_dev,
            metadata.st_ino,
            database_metadata.st_dev,
            database_metadata.st_ino,
        )
        if trusted_identity is None:
            raise PermissionError(
                "Persistent storage has not passed startup validation"
            )
        if trusted_identity != actual_identity:
            raise PermissionError(
                "Persistent application storage changed since startup"
            )

        # Lock the stable data-directory inode itself, rather than a replaceable
        # lock file, then confirm its pathname still identifies the locked inode.
        path_metadata = os.stat(data_dir, follow_symlinks=False)
        if (metadata.st_dev, metadata.st_ino) != (
            path_metadata.st_dev,
            path_metadata.st_ino,
        ):
            raise PermissionError("Firewall mutation lock directory changed")

        keep_descriptor = True
        return descriptor, database_descriptor
    finally:
        if not keep_descriptor:
            if database_descriptor is not None:
                os.close(database_descriptor)
            os.close(descriptor)


def _release_mutation_lock(directory_descriptor: int, database_descriptor: int) -> None:
    try:
        fcntl.flock(directory_descriptor, fcntl.LOCK_UN)
    finally:
        try:
            os.close(database_descriptor)
        finally:
            os.close(directory_descriptor)


@asynccontextmanager
async def recovery_state_lock() -> AsyncIterator[None]:
    """Serialize marker inspection and firewall work across app processes."""
    owner = asyncio.current_task()
    if owner is None:
        raise RuntimeError("Recovery state lock requires an active asyncio task")
    inherited_owner = _MUTATION_LOCK_OWNER.get()
    if inherited_owner is owner:
        ensure_recovery_directory_stable()
        yield
        return
    if inherited_owner is not None:
        raise HTTPException(status_code=503, detail=RECOVERY_STATE_UNAVAILABLE)

    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    descriptors = None

    while descriptors is None:
        try:
            descriptors = _try_acquire_mutation_lock()
        except OSError as exc:
            logger.error(
                "Could not acquire recovery state lock (%s).", type(exc).__name__
            )
            raise HTTPException(
                status_code=503, detail=RECOVERY_STATE_UNAVAILABLE
            ) from exc

        if descriptors is not None:
            descriptor, database_descriptor = descriptors
            try:
                _assert_recovery_directory_identity(descriptor)
                _assert_recovery_database_identity(descriptor, database_descriptor)
                if not filesystem_service._application_database_is_valid(
                    descriptor, database_descriptor
                ):
                    raise PermissionError("Persistent application database is invalid")
                _assert_recovery_directory_identity(descriptor)
                _assert_recovery_database_identity(descriptor, database_descriptor)
            except OSError as exc:
                _release_mutation_lock(descriptor, database_descriptor)
                logger.error(
                    "Recovery storage validation failed during lock acquisition (%s).",
                    type(exc).__name__,
                )
                raise HTTPException(
                    status_code=503, detail=RECOVERY_STATE_UNAVAILABLE
                ) from exc
            break
        if time.monotonic() >= deadline:
            logger.warning("Recovery state lock acquisition timed out.")
            raise HTTPException(status_code=503, detail=LOCK_TIMEOUT)
        await asyncio.sleep(LOCK_RETRY_SECONDS)

    descriptor_token = _MUTATION_LOCK_DESCRIPTOR.set(descriptor)
    database_token = _MUTATION_DATABASE_DESCRIPTOR.set(database_descriptor)
    owner_token = _MUTATION_LOCK_OWNER.set(owner)
    try:
        yield
    finally:
        try:
            _MUTATION_LOCK_OWNER.reset(owner_token)
        finally:
            try:
                _MUTATION_DATABASE_DESCRIPTOR.reset(database_token)
            finally:
                try:
                    _MUTATION_LOCK_DESCRIPTOR.reset(descriptor_token)
                finally:
                    _release_mutation_lock(descriptor, database_descriptor)


@asynccontextmanager
async def firewall_mutation_guard() -> AsyncIterator[None]:
    """Admit a firewall mutation only after checking recovery state under lock."""
    async with recovery_state_lock():
        if has_unresolved_recovery_marker():
            raise HTTPException(status_code=503, detail=MANUAL_RECOVERY_REQUIRED)
        yield


def protect_firewall_mutation(
    handler: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """Hold the shared recovery guard for the complete async route operation."""

    @wraps(handler)
    async def guarded(*args: P.args, **kwargs: P.kwargs) -> R:
        async with firewall_mutation_guard():
            return await handler(*args, **kwargs)

    return guarded
