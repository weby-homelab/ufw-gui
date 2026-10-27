"""
UFW-GUI - Subprocess execution service
Handles all system command execution with argument validation
"""

from subprocess import CalledProcessError, CompletedProcess, run

from fastapi import HTTPException

from backend.services.async_operations import run_to_thread_to_completion
from backend.services.recovery_guard import (
    ensure_firewall_mutation_admitted,
    ensure_firewall_subprocess_admitted,
    mutation_lock_descriptors,
)
from backend.utils.validators import validate_args


async def _run_command(command: list[str]) -> CompletedProcess[str]:
    ensure_firewall_mutation_admitted()
    lock_descriptors = mutation_lock_descriptors()
    return await run_to_thread_to_completion(
        _run_with_final_recovery_check,
        command,
        lock_descriptors,
    )


def _run_with_final_recovery_check(
    command: list[str],
    lock_descriptors: tuple[int, int] | None,
) -> CompletedProcess[str]:
    pass_fds: tuple[int, ...] = ()
    if lock_descriptors is not None:
        directory_descriptor, database_descriptor = lock_descriptors
        ensure_firewall_subprocess_admitted(directory_descriptor, database_descriptor)
        pass_fds = (directory_descriptor,)
    return run(
        command,
        capture_output=True,
        text=True,
        check=True,
        pass_fds=pass_fds,
    )


async def run_ufw(*args) -> str:
    safe_args = validate_args(args)
    try:
        result = await _run_command(["ufw"] + safe_args)
        return result.stdout.strip()
    except CalledProcessError:
        raise HTTPException(
            status_code=500, detail="UFW command failed. Check system logs."
        )


async def run_fail2ban(*args) -> str:
    safe_args = validate_args(args)
    try:
        result = await _run_command(["fail2ban-client"] + safe_args)
        return result.stdout.strip()
    except CalledProcessError:
        raise HTTPException(
            status_code=500, detail="Fail2Ban command failed. Check system logs."
        )
