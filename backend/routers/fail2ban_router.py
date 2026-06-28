"""
UFW-GUI - Fail2Ban router
"""
from fastapi import APIRouter, Body, Depends, HTTPException
import re

from backend.services.auth_service import get_current_user
from backend.services.subprocess_service import run_fail2ban
from backend.services.database_service import log_action
from backend.utils.validators import is_valid_ip, is_valid_jail

router = APIRouter(prefix="/api/fail2ban", tags=["Fail2Ban"])


@router.get("/status")
async def get_f2b_status(user=Depends(get_current_user)):
    try:
        status_out = await run_fail2ban("status")
        jails_match = re.search(r"Jail list:\s+(.*)", status_out)
        if not jails_match:
            return {"banned": []}

        jails = jails_match.group(1).split(", ")
        banned = []
        for j in jails:
            if not is_valid_jail(j):
                continue
            jail_status = await run_fail2ban("status", j)
            ips = jail_status.split("Banned IP list:")[-1].strip().split()
            for ip in ips:
                banned.append({"ip": ip, "jail": j})
        return {"banned": banned}
    except Exception:
        return {"banned": []}


@router.post("/unban")
async def unban_ip(
    ip: str = Body(...),
    jail: str = Body(...),
    user=Depends(get_current_user),
):
    if not is_valid_ip(ip):
        raise HTTPException(status_code=400, detail="Invalid IP")
    if not is_valid_jail(jail):
        raise HTTPException(status_code=400, detail="Invalid Jail")
    res = await run_fail2ban("set", jail, "unbanip", ip)
    log_action(user["username"], "UNBAN", f"IP: {ip}, Jail: {jail}")
    return {"result": res}
