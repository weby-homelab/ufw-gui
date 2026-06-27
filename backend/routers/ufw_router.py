"""
UFW-GUI - UFW firewall router
"""
from fastapi import APIRouter, Body, Depends, HTTPException
from typing import Literal
from datetime import datetime
import re

from backend.services.auth_service import get_current_user
from backend.services.subprocess_service import run_ufw, run_fail2ban
from backend.services.filesystem_service import create_snapshot
from backend.services.database_service import log_action
from backend.utils.validators import is_valid_ip, is_valid_port, is_valid_proto

router = APIRouter(prefix="/api", tags=["UFW"])


@router.get("/status")
async def get_status(user=Depends(get_current_user)):
    try:
        status = run_ufw("status")
        return {"status": "running" if "Status: active" in status else "inactive"}
    except Exception:
        return {"status": "unknown"}


@router.post("/toggle")
async def toggle_ufw(
    action: str = Body(..., embed=True),
    user=Depends(get_current_user),
):
    if action not in ["enable", "disable", "reload"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    res = run_ufw("--force", action)
    log_action(user["username"], "TOGGLE_UFW", action)
    return {"result": res}


@router.get("/rules")
async def get_rules(user=Depends(get_current_user)):
    try:
        output = run_ufw("status", "numbered")
        rules = []
        pattern = r"\[\s*(\d+)\]\s+(.*?)\s+(ALLOW IN|DENY IN|REJECT IN|ALLOW OUT|DENY OUT|ALLOW|DENY|REJECT)\s+(.*)"
        for line in output.split("\n"):
            match = re.match(pattern, line)
            if match:
                rules.append({
                    "id": match.group(1),
                    "to": match.group(2).strip(),
                    "action": match.group(3).strip(),
                    "from": match.group(4).strip(),
                    "raw": line,
                })
        return {"rules": rules}
    except Exception:
        return {"rules": [], "error": "Failed to fetch rules. Check system logs."}


@router.post("/rule")
async def add_rule(
    action: str = Body(...),
    port: str = Body(""),
    proto: str = Body(""),
    ip: str = Body(""),
    user=Depends(get_current_user),
):
    if action not in ["allow", "deny", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    if not is_valid_ip(ip):
        raise HTTPException(status_code=400, detail="Invalid IP format")
    if not is_valid_port(port):
        raise HTTPException(status_code=400, detail="Invalid Port format")
    if not is_valid_proto(proto):
        raise HTTPException(status_code=400, detail="Invalid Protocol")

    create_snapshot("before_add_rule")
    args = [action]
    if ip:
        args.extend(["from", ip])
        if port:
            args.extend(["to", "any", "port", port])
            if proto:
                args.extend(["proto", proto])
    else:
        if port:
            target = port if not proto else f"{port}/{proto}"
            args.append(target)

    res = run_ufw(*args)
    log_action(user["username"], "ADD_RULE", f"Action: {action}, Target: {port}, IP: {ip}")
    return {"result": res}


@router.delete("/rule/{rule_id}")
async def delete_rule(rule_id: str, user=Depends(get_current_user)):
    if not rule_id.isdigit():
        raise HTTPException(status_code=400, detail="Invalid ID")
    create_snapshot("before_del_rule")
    res = run_ufw("--force", "delete", rule_id)
    log_action(user["username"], "DELETE_RULE", f"ID: {rule_id}")
    return {"result": res}


@router.post("/ban")
async def ban_ip(
    ip: str = Body(..., embed=True),
    user=Depends(get_current_user),
):
    if not is_valid_ip(ip):
        raise HTTPException(status_code=400, detail="Invalid IP format")
    create_snapshot("before_ban")
    res = run_ufw("insert", "1", "deny", "from", ip)
    log_action(user["username"], "BAN_IP", ip)
    return {"result": res}


@router.post("/reload")
async def reload_firewall(user=Depends(get_current_user)):
    res = run_ufw("reload")
    log_action(user["username"], "RELOAD", "System")
    return {"result": res}
