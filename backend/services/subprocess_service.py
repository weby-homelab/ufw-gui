"""
UFW-GUI - Subprocess execution service
Handles all system command execution with argument validation
"""
from fastapi import HTTPException
from subprocess import run, CalledProcessError
from backend.utils.validators import validate_args


def run_ufw(*args) -> str:
    safe_args = validate_args(args)
    try:
        result = run(["ufw"] + safe_args, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except CalledProcessError as e:
        raise HTTPException(status_code=500, detail="UFW command failed. Check system logs.")


def run_fail2ban(*args) -> str:
    safe_args = validate_args(args)
    try:
        result = run(["fail2ban-client"] + safe_args, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except CalledProcessError as e:
        raise HTTPException(status_code=500, detail="Fail2Ban command failed. Check system logs.")
