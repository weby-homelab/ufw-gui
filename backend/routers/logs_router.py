"""
UFW-GUI - Logs and statistics router
"""

import asyncio
import logging
import os
import re
import sqlite3

from fastapi import APIRouter, Depends

from backend.services.auth_service import get_current_user
from backend.services.database_service import get_stats_last_24h

current_user_dependency = Depends(get_current_user)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Logs"])


def _read_log_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="replace") as log_file:
        return log_file.readlines()


@router.get("/logs")
async def get_ufw_logs(user=current_user_dependency):
    lines = []
    log_path = (
        "/var/log/ufw.log" if os.path.exists("/var/log/ufw.log") else "/var/log/syslog"
    )
    if not os.path.exists(log_path):
        return {"logs": []}

    try:
        lines = await asyncio.to_thread(_read_log_lines, log_path)
    except OSError as exc:
        logger.warning("Could not read UFW logs (%s).", type(exc).__name__)
        return {"logs": [], "error": "UFW logs are unavailable."}

    parsed = []
    for line in lines[-500:]:
        if "[UFW BLOCK]" in line or "[UFW REJECT]" in line:
            src = re.search(r"SRC=([\d\.]+)", line)
            proto = re.search(r"PROTO=(\w+)", line)
            dpt = re.search(r"DPT=(\d+)", line)
            if src:
                item = {
                    "time": line[:15],
                    "src": src.group(1),
                    "proto": proto.group(1) if proto else "?",
                    "port": dpt.group(1) if dpt else "?",
                }
                parsed.append(item)

    return {"logs": parsed[::-1][:40]}


@router.get("/stats")
async def get_stats(user=current_user_dependency):
    try:
        hourly = get_stats_last_24h()
        return {"hourly": hourly}
    except sqlite3.Error as exc:
        logger.warning("Could not load firewall statistics (%s).", type(exc).__name__)
        return {"hourly": [], "error": "Statistics are unavailable."}
