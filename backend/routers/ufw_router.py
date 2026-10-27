"""
UFW-GUI - UFW firewall router
"""

import logging
import re

from fastapi import APIRouter, Body, Depends, HTTPException

from backend.services.auth_service import get_current_user
from backend.services.database_service import log_action
from backend.services.recovery_guard import protect_firewall_mutation
from backend.services.subprocess_service import run_ufw
from backend.utils.validators import is_valid_ip, is_valid_port, is_valid_proto

current_user_dependency = Depends(get_current_user)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["UFW"])


@router.get("/status")
async def get_status(user=current_user_dependency):
    try:
        status = await run_ufw("status")
        return {"status": "running" if "Status: active" in status else "inactive"}
    except HTTPException:
        raise
    except OSError as exc:
        logger.warning("Could not read UFW status (%s).", type(exc).__name__)
        return {"status": "unknown", "error": "UFW status is unavailable."}


@router.post("/toggle")
@protect_firewall_mutation
async def toggle_ufw(
    action: str = Body(..., embed=True),
    user=current_user_dependency,
):
    if action not in ["enable", "disable", "reload"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    res = await run_ufw("--force", action)
    log_action(user["username"], "TOGGLE_UFW", action)
    return {"result": res}


@router.get("/rules")
async def get_rules(user=current_user_dependency):
    try:
        output = await run_ufw("status", "numbered")
        rules = []
        pattern = r"\[\s*(\d+)\]\s+(.*?)\s+(ALLOW IN|DENY IN|REJECT IN|ALLOW OUT|DENY OUT|ALLOW|DENY|REJECT)\s+(.*)"
        for line in output.split("\n"):
            match = re.match(pattern, line)
            if match:
                rules.append(
                    {
                        "id": match.group(1),
                        "to": match.group(2).strip(),
                        "action": match.group(3).strip(),
                        "from": match.group(4).strip(),
                        "raw": line,
                    }
                )
        return {"rules": rules}
    except HTTPException:
        raise
    except OSError as exc:
        logger.warning("Could not read UFW rules (%s).", type(exc).__name__)
        return {"rules": [], "error": "Failed to fetch rules. Check system logs."}


@router.post("/rule")
@protect_firewall_mutation
async def add_rule(
    action: str = Body(...),
    port: str = Body(""),
    proto: str = Body(""),
    ip: str = Body(""),
    user=current_user_dependency,
):
    if action not in ["allow", "deny", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    if not is_valid_ip(ip):
        raise HTTPException(status_code=400, detail="Invalid IP format")
    if not is_valid_port(port):
        raise HTTPException(status_code=400, detail="Invalid Port format")
    if not is_valid_proto(proto):
        raise HTTPException(status_code=400, detail="Invalid Protocol")

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

    res = await run_ufw(*args)
    log_action(
        user["username"], "ADD_RULE", f"Action: {action}, Target: {port}, IP: {ip}"
    )
    return {"result": res}


@router.delete("/rule/{rule_id}")
@protect_firewall_mutation
async def delete_rule(rule_id: str, user=current_user_dependency):
    if not rule_id.isdigit():
        raise HTTPException(status_code=400, detail="Invalid ID")
    res = await run_ufw("--force", "delete", rule_id)
    log_action(user["username"], "DELETE_RULE", f"ID: {rule_id}")
    return {"result": res}


@router.post("/ban")
@protect_firewall_mutation
async def ban_ip(
    ip: str = Body(..., embed=True),
    user=current_user_dependency,
):
    if not ip:
        raise HTTPException(status_code=400, detail="IP is required")
    if not is_valid_ip(ip):
        raise HTTPException(status_code=400, detail="Invalid IP format")
    res = await run_ufw("insert", "1", "deny", "from", ip)
    log_action(user["username"], "BAN_IP", ip)
    return {"result": res}


@router.post("/reload")
@protect_firewall_mutation
async def reload_firewall(user=current_user_dependency):
    res = await run_ufw("reload")
    log_action(user["username"], "RELOAD", "System")
    return {"result": res}
