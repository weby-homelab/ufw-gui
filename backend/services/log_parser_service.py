"""
UFW-GUI - Log parser service
Reads UFW block logs in a non-blocking background task and stores them in SQLite for statistics
"""

import asyncio
import logging
import os
import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime

from backend.services.sqlite_utils import connect_existing_database

DATA_DIR = "/app/data"
DB_FILE = f"{DATA_DIR}/stats.db"
LOG_PATHS = ["/var/log/ufw.log", "/var/log/syslog"]
logger = logging.getLogger(__name__)


async def start_log_parser():
    log_path = None
    for p in LOG_PATHS:
        if os.path.exists(p):
            log_path = p
            break

    if not log_path:
        logger.warning("No log files found. Statistics parser disabled.")
        return

    # Seek to end on startup to only parse new logs
    try:
        stat = os.stat(log_path)
        offset = stat.st_size
        inode = stat.st_ino
    except OSError as exc:
        logger.warning("Could not inspect the firewall log (%s).", type(exc).__name__)
        offset = 0
        inode = None

    while True:
        try:
            await asyncio.sleep(5)
            if not os.path.exists(log_path):
                inode = None
                continue

            try:
                stat = os.stat(log_path)
                curr_size = stat.st_size
                curr_inode = stat.st_ino
            except FileNotFoundError:
                inode = None
                continue

            # Detect log rotation: inode changed or size decreased
            if inode is not None and (curr_inode != inode or curr_size < offset):
                logger.info("Log rotation detected. Resetting offset.")
                offset = 0
                inode = curr_inode

            if curr_size > offset:
                await parse_logs_range(log_path, offset, curr_size)
                offset = curr_size
                inode = curr_inode
        except asyncio.CancelledError:
            break
        except (OSError, sqlite3.Error) as exc:
            logger.error("Log parser iteration failed (%s).", type(exc).__name__)


async def parse_logs_range(path: str, start: int, end: int):
    try:

        def read_chunk():
            with open(path, "r", errors="ignore") as f:
                f.seek(start)
                return f.read(end - start)

        content = await asyncio.to_thread(read_chunk)
    except OSError as exc:
        logger.warning("Could not read firewall log chunk (%s).", type(exc).__name__)
        return

    lines = content.splitlines()
    drops = []

    for line in lines:
        if "[UFW BLOCK]" in line or "[UFW REJECT]" in line:
            src = re.search(r"SRC=([\d\.\:a-fA-F]+)", line)
            proto = re.search(r"PROTO=(\w+)", line)
            dpt = re.search(r"DPT=(\d+)", line)

            if src:
                src_ip = src.group(1)
                proto_str = proto.group(1) if proto else "?"
                port_str = dpt.group(1) if dpt else "?"
                ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
                drops.append((ts, src_ip, proto_str, port_str))

    if drops:

        def write_drops():
            with closing(connect_existing_database(DB_FILE)) as conn, conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO drops (ts, src, proto, port) VALUES (?, ?, ?, ?)",
                    drops,
                )

        try:
            await asyncio.to_thread(write_drops)
        except sqlite3.Error as exc:
            logger.error(
                "Failed to write firewall statistics (%s).", type(exc).__name__
            )
