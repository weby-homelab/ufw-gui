"""
UFW-GUI - Logs and statistics router
"""
from fastapi import APIRouter, Depends
import re
import os

from backend.services.auth_service import get_current_user
from backend.services.database_service import get_stats_last_24h

router = APIRouter(prefix="/api", tags=["Logs"])


@router.get("/logs")
async def get_ufw_logs(user=Depends(get_current_user)):
    lines = []
    log_path = "/var/log/ufw.log" if os.path.exists("/var/log/ufw.log") else "/var/log/syslog"
    if not os.path.exists(log_path):
        return {"logs": []}

    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
    except Exception:
        return {"logs": []}

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
async def get_stats(user=Depends(get_current_user)):
    try:
        hourly = get_stats_last_24h()
        return {"hourly": hourly}
    except Exception:
        return {"hourly": []}
