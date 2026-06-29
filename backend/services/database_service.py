"""
UFW-GUI - Database service
Handles SQLite operations for drops and audit logs
"""
import os
import json
import sqlite3
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = "/app/data"
DB_FILE = f"{DATA_DIR}/stats.db"

# Expose a thread pool executor with maximum 2 threads to queue/throttling alerts
_tg_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tg_alerts")


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-8000;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drops 
        (id INTEGER PRIMARY KEY, ts TIMESTAMP, src TEXT, proto TEXT, port TEXT, 
         UNIQUE(ts, src, port))
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs 
        (id INTEGER PRIMARY KEY, ts TIMESTAMP, username TEXT, action TEXT, details TEXT)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users 
        (username TEXT PRIMARY KEY, password TEXT, role TEXT)
    """)
    conn.commit()
    conn.close()


def log_action(username: str, action: str, details: str):
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute(
            "INSERT INTO audit_logs (ts, username, action, details) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), username, action, str(details))
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save action to audit log: {e}")
    finally:
        conn.close()

    try:
        # Submit Telegram alert task to thread pool instead of spawning a new OS thread
        _tg_executor.submit(_send_tg_alert, username, action, details)
    except Exception as e:
        logger.error(f"Failed to submit Telegram alert: {e}")


def shutdown_db():
    _tg_executor.shutdown(wait=False)


def _send_tg_alert(username: str, action: str, details: str):
    config_file = f"{DATA_DIR}/config.json"
    if not os.path.exists(config_file):
        return
    try:
        with open(config_file, "r") as f:
            cfg = json.load(f)
        t = cfg.get("tg_token")
        c = cfg.get("tg_chat_id")
        if t and c:
            import requests
            text = f"🛡️ *UFW Action*\n👤 User: {username}\n🎯 Action: {action}\n📝 Details: {details}"
            response = requests.post(
                f"https://api.telegram.org/bot{t}/sendMessage",
                json={"chat_id": c, "text": text, "parse_mode": "Markdown"},
                timeout=5
            )
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")


def get_recent_drops(limit: int = 500) -> list:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM drops WHERE ts > datetime('now', '-24 hours') ORDER BY ts DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stats_last_24h() -> list:
    conn = sqlite3.connect(DB_FILE)
    query = """
        SELECT strftime('%H:', ts) || (CAST(strftime('%M', ts) AS INTEGER) / 10) || '0' as interval, 
               count(*) as count
        FROM drops 
        WHERE ts > datetime('now', '-24 hours') 
        GROUP BY interval 
        ORDER BY interval ASC
    """
    res = conn.execute(query).fetchall()
    conn.close()
    return [{"hour": r[0], "count": r[1]} for r in res]


def get_audit_logs(limit: int = 50) -> list:
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute(
        "SELECT ts, username, action, details FROM audit_logs ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [{"ts": r[0], "user": r[1], "action": r[2], "details": r[3]} for r in rows]
