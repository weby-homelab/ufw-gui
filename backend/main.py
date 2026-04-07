from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import subprocess, json, os, re, shutil, asyncio, sqlite3, requests

# Security Hardening: Load secret from environment
SECRET_KEY = os.getenv("UFW_GUI_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("FATAL: UFW_GUI_SECRET_KEY environment variable is not set!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

DATA_DIR = "/app/data"
USER_DATA_FILE = f"{DATA_DIR}/users.json"
CONFIG_FILE = f"{DATA_DIR}/config.json"
UFW_BACKUP_DIR = f"{DATA_DIR}/ufw_backups"
DB_FILE = f"{DATA_DIR}/stats.db"

app = FastAPI(title="UFW-GUI API")
rollback_task = None

# Tighten CORS: Require explicit origins or default to localhost
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not allowed_origins or allowed_origins == [""]:
    allowed_origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Validation Helpers ---
def is_valid_ip(ip: str) -> bool:
    if not ip: return True
    # Basic IPv4/IPv6 regex
    ipv4 = r"^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$"
    ipv6 = r"^[0-9a-fA-F:]+(\/\d{1,3})?$"
    return bool(re.match(ipv4, ip)) or bool(re.match(ipv6, ip))

def is_valid_port(port: str) -> bool:
    if not port: return True
    # Allow numbers, ranges like 80:90
    return bool(re.match(r"^\d+(:\d+)?$", port))

def is_valid_proto(proto: str) -> bool:
    if not proto: return True
    return proto.lower() in ["tcp", "udp"]

# --- Database ---
def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS drops (id INTEGER PRIMARY KEY, ts TIMESTAMP, src TEXT, proto TEXT, port TEXT, UNIQUE(ts, src, port))")
    conn.execute("CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY, ts TIMESTAMP, username TEXT, action TEXT, details TEXT)")
    conn.commit()
    conn.close()

init_db()

def log_action(username, action, details):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO audit_logs (ts, username, action, details) VALUES (?, ?, ?, ?)", (datetime.now().isoformat(), username, action, str(details)))
    conn.commit()
    conn.close()
    send_tg_alert(f"🛡️ *UFW Action*\n👤 User: {username}\n🎯 Action: {action}\n📝 Details: {details}")

def send_tg_alert(text):
    if not os.path.exists(CONFIG_FILE): return
    try:
        with open(CONFIG_FILE, "r") as f: cfg = json.load(f)
        t = cfg.get("tg_token"); c = cfg.get("tg_chat_id")
        if t and c: requests.post(f"https://api.telegram.org/bot{t}/sendMessage", json={"chat_id": c, "text": text, "parse_mode": "Markdown"}, timeout=1.5)
    except: pass

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e: raise HTTPException(status_code=500, detail=e.stderr)

def load_users():
    if not os.path.exists(USER_DATA_FILE): return {}
    with open(USER_DATA_FILE, "r") as f: return json.load(f)

def save_users(users):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USER_DATA_FILE, "w") as f: json.dump(users, f)

def create_snapshot(label="auto"):
    os.makedirs(UFW_BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_path = f"{UFW_BACKUP_DIR}/snap_{ts}_{label}"
    if os.path.exists("/etc/ufw"):
        shutil.copytree("/etc/ufw", snap_path, dirs_exist_ok=True)
    return ts

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        users = load_users()
        if username not in users: raise HTTPException(status_code=401)
        return {"username": username, "role": users[username].get("role", "admin")}
    except JWTError: raise HTTPException(status_code=401)

# === Auth ===
@app.get("/api/auth/setup-needed")
async def is_setup_needed(): return {"setup_needed": len(load_users()) == 0}

@app.post("/api/auth/setup")
async def setup_admin(username: str = Body(...), password: str = Body(...)):
    users = load_users()
    if len(users) > 0: raise HTTPException(status_code=400)
    users[username] = {"password": pwd_context.hash(password), "role": "superadmin"}
    save_users(users)
    log_action(username, "SETUP", "Superadmin created")
    return {"status": "success"}

@app.post("/api/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    users = load_users()
    u = users.get(form_data.username)
    if not u or not pwd_context.verify(form_data.password, u["password"]): raise HTTPException(status_code=401)
    t = jwt.encode({"sub": form_data.username, "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": t, "token_type": "bearer"}

@app.get("/api/auth/me")
async def get_me(u=Depends(get_current_user)): return u

# === UFW Core ===
@app.get("/api/status")
async def get_status(u=Depends(get_current_user)):
    try:
        status = run_cmd(["ufw", "status"])
        return {"status": "running" if "Status: active" in status else "inactive"}
    except: return {"status": "unknown"}

@app.post("/api/toggle")
async def toggle_ufw(action: str = Body(..., embed=True), u=Depends(get_current_user)):
    if action not in ["enable", "disable", "reload"]: raise HTTPException(status_code=400, detail="Invalid action")
    res = run_cmd(["ufw", "--force", action])
    log_action(u["username"], "TOGGLE_UFW", action)
    return {"result": res}

@app.get("/api/rules")
async def get_rules(u=Depends(get_current_user)):
    try:
        output = run_cmd(["ufw", "status", "numbered"])
        rules = []
        lines = output.split("\n")
        for line in lines:
            match = re.match(r"\[\s*(\d+)\]\s+(.*?)\s+(ALLOW IN|DENY IN|REJECT IN|ALLOW OUT|DENY OUT|ALLOW|DENY|REJECT)\s+(.*)", line)
            if match:
                rules.append({
                    "id": match.group(1),
                    "to": match.group(2).strip(),
                    "action": match.group(3).strip(),
                    "from": match.group(4).strip(),
                    "raw": line
                })
        return {"rules": rules}
    except Exception as e:
        return {"rules": [], "error": str(e)}

@app.post("/api/rule")
async def add_rule(action: str = Body(...), port: str = Body(""), proto: str = Body(""), ip: str = Body(""), u=Depends(get_current_user)):
    # Input Validation
    if action not in ["allow", "deny", "reject"]: raise HTTPException(status_code=400, detail="Invalid action")
    if not is_valid_ip(ip): raise HTTPException(status_code=400, detail="Invalid IP format")
    if not is_valid_port(port): raise HTTPException(status_code=400, detail="Invalid Port format")
    if not is_valid_proto(proto): raise HTTPException(status_code=400, detail="Invalid Protocol")

    create_snapshot("before_add_rule")
    cmd = ["ufw", action]
    if ip:
        cmd.extend(["from", ip])
        if port:
            cmd.extend(["to", "any", "port", port])
            if proto:
                cmd.extend(["proto", proto])
    else:
        target = port if not proto else f"{port}/{proto}"
        cmd.append(target)
    
    res = run_cmd(cmd)
    log_action(u["username"], "ADD_RULE", f"Action: {action}, Target: {port}, IP: {ip}")
    return {"result": res}

@app.delete("/api/rule/{rule_id}")
async def delete_rule(rule_id: str, u=Depends(get_current_user)):
    if not rule_id.isdigit(): raise HTTPException(status_code=400, detail="Invalid ID")
    create_snapshot("before_del_rule")
    res = run_cmd(["ufw", "--force", "delete", rule_id])
    log_action(u["username"], "DELETE_RULE", f"ID: {rule_id}")
    return {"result": res}

@app.post("/api/ban")
async def ban_ip(ip: str = Body(..., embed=True), u=Depends(get_current_user)):
    if not is_valid_ip(ip): raise HTTPException(status_code=400, detail="Invalid IP format")
    create_snapshot("before_ban")
    res = run_cmd(["ufw", "insert", "1", "deny", "from", ip])
    log_action(u["username"], "BAN_IP", ip)
    return {"result": res}

# === Logs & Stats ===
@app.get("/api/logs")
async def get_ufw_logs(u=Depends(get_current_user)):
    try:
        with open("/var/log/ufw.log", "r") as f: lines = f.readlines()
    except:
        try:
            with open("/var/log/syslog", "r") as f: lines = f.readlines()
        except:
            return {"logs": []}

    parsed = []
    conn = sqlite3.connect(DB_FILE)
    for line in lines[-500:]:
        if "[UFW BLOCK]" in line or "[UFW REJECT]" in line:
            src = re.search(r"SRC=([\d\.]+)", line)
            proto = re.search(r"PROTO=(\w+)", line)
            dpt = re.search(r"DPT=(\d+)", line)
            if src: 
                item = {"time": line[:15], "src": src.group(1), "proto": proto.group(1) if proto else "?", "port": dpt.group(1) if dpt else "?"}
                parsed.append(item)
                conn.execute("INSERT OR IGNORE INTO drops (ts, src, proto, port) VALUES (?, ?, ?, ?)", (datetime.now().isoformat(), item["src"], item["proto"], item["port"]))
    conn.commit()
    conn.close()
    return {"logs": parsed[::-1][:40]}

@app.get("/api/stats")
async def get_stats(u=Depends(get_current_user)):
    conn = sqlite3.connect(DB_FILE)
    query = "SELECT strftime('%H:', ts) || (CAST(strftime('%M', ts) AS INTEGER) / 10) || '0' as interval, count(*) FROM drops WHERE ts > datetime('now', '-24 hours') GROUP BY date(ts), strftime('%H', ts), (CAST(strftime('%M', ts) AS INTEGER) / 10) ORDER BY date(ts), strftime('%H', ts), (CAST(strftime('%M', ts) AS INTEGER) / 10)"
    res = conn.execute(query).fetchall()
    conn.close()
    return {"hourly": [{"hour": r[0], "count": r[1]} for r in res]}

# === Fail2Ban ===
@app.get("/api/fail2ban/status")
async def get_f2b(u=Depends(get_current_user)):
    try:
        jails = re.search(r"Jail list:\s+(.*)", run_cmd(["fail2ban-client", "status"])).group(1).split(", ")
        banned = []
        for j in jails:
            ips = run_cmd(["fail2ban-client", "status", j]).split("Banned IP list:")[-1].strip().split()
            for ip in ips: banned.append({"ip": ip, "jail": j})
        return {"banned": banned}
    except: return {"banned": []}

@app.post("/api/fail2ban/unban")
async def unban(ip: str=Body(...), jail: str=Body(...), u=Depends(get_current_user)):
    if not is_valid_ip(ip): raise HTTPException(status_code=400, detail="Invalid IP")
    res = run_cmd(["fail2ban-client", "set", jail, "unbanip", ip])
    log_action(u["username"], "UNBAN", f"IP: {ip}, Jail: {jail}")
    return {"result": res}

# === Admin & Settings ===
@app.get("/api/audit-logs")
async def get_audit(u=Depends(get_current_user)):
    conn = sqlite3.connect(DB_FILE)
    res = conn.execute("SELECT ts, username, action, details FROM audit_logs ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return {"logs": [{"ts": r[0], "user": r[1], "action": r[2], "details": r[3]} for r in res]}

@app.get("/api/users")
async def get_users(u=Depends(get_current_user)):
    if u["role"] != "superadmin": raise HTTPException(status_code=403)
    users = load_users()
    return [{"username": name, "role": d.get("role")} for name, d in users.items()]

@app.post("/api/users")
async def add_user(username: str=Body(...), password: str=Body(...), u=Depends(get_current_user)):
    if u["role"] != "superadmin": raise HTTPException(status_code=403)
    users = load_users()
    users[username] = {"password": pwd_context.hash(password), "role": "admin"}
    save_users(users)
    log_action(u["username"], "ADD_USER", username)
    return {"status": "success"}

@app.delete("/api/users/{t}")
async def del_user(t: str, u=Depends(get_current_user)):
    if u["role"] != "superadmin": raise HTTPException(status_code=403)
    users = load_users()
    del users[t]
    save_users(users)
    log_action(u["username"], "DEL_USER", t)
    return {"status": "success"}

@app.get("/api/settings")
async def get_set(u=Depends(get_current_user)):
    return json.load(open(CONFIG_FILE, "r")) if os.path.exists(CONFIG_FILE) else {}

@app.post("/api/settings")
async def save_set(data: dict=Body(...), u=Depends(get_current_user)):
    if u["role"] != "superadmin": raise HTTPException(status_code=403)
    with open(CONFIG_FILE, "w") as f: json.dump(data, f)
    return {"status": "success"}

@app.get("/api/snapshots/all")
async def get_snaps(u=Depends(get_current_user)):
    return {"snapshots": sorted(os.listdir(UFW_BACKUP_DIR), reverse=True)} if os.path.exists(UFW_BACKUP_DIR) else {"snapshots": []}

@app.post("/api/snapshots/restore/{n}")
async def restore_sn(n: str, u=Depends(get_current_user)):
    if ".." in n or "/" in n: raise HTTPException(status_code=400)
    snap_path = os.path.join(UFW_BACKUP_DIR, n)
    shutil.copytree(snap_path, "/etc/ufw", dirs_exist_ok=True)
    run_cmd(["ufw", "reload"])
    log_action(u["username"], "RESTORE", n)
    return {"status": "success"}

# === Test Rule / Rollback ===
async def perform_rollback():
    await asyncio.sleep(60)
    fallback_path = os.path.join(UFW_BACKUP_DIR, "test_rollback_config")
    if os.path.exists(fallback_path):
        shutil.copytree(fallback_path, "/etc/ufw", dirs_exist_ok=True)
        run_cmd(["ufw", "reload"])
        log_action("SYSTEM", "ROLLBACK", "Auto-reverted untested changes after 60s")

@app.post("/api/reload/test")
async def reload_test(u=Depends(get_current_user)):
    global rollback_task
    if rollback_task and not rollback_task.done(): rollback_task.cancel()
    
    os.makedirs(UFW_BACKUP_DIR, exist_ok=True)
    fallback_path = os.path.join(UFW_BACKUP_DIR, "test_rollback_config")
    
    # Clean up existing fallback to avoid FileExistsError
    if os.path.exists(fallback_path):
        if os.path.isdir(fallback_path): shutil.rmtree(fallback_path)
        else: os.remove(fallback_path)
        
    if os.path.exists("/etc/ufw"):
        shutil.copytree("/etc/ufw", fallback_path, dirs_exist_ok=True)
    
    res = run_cmd(["ufw", "reload"])
    log_action(u["username"], "TEST_RELOAD", "Testing firewall changes for 60s")
    rollback_task = asyncio.create_task(perform_rollback())
    return {"status": "testing", "result": res}

@app.post("/api/reload/confirm")
async def reload_confirm(u=Depends(get_current_user)):
    global rollback_task
    if rollback_task and not rollback_task.done():
        rollback_task.cancel()
        log_action(u["username"], "CONFIRM", "Changes confirmed")
        return {"status": "confirmed"}
    return {"status": "no_active_test"}

@app.post("/api/reload")
async def reload_f(u=Depends(get_current_user)):
    res = run_cmd(["ufw", "reload"]); log_action(u["username"], "RELOAD", "System"); return {"result": res}
