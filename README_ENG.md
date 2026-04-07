# 🛡️ UFW-GUI v1.4.0 — NETWORK SECURITY (Security Hardening Release)


[![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest)
[![Docker Pulls](https://img.shields.io/docker/pulls/webyhomelab/ufw-gui-backend)](https://hub.docker.com/r/webyhomelab/ufw-gui-backend)

A modern, fast, and secure web interface for managing the **UFW** firewall on Ubuntu/Debian servers.

## 🛡️ What's New in v1.4.0 (Security Hardening)
- **Zero-Fallback Secrets:** The app will not start without a defined `UFW_GUI_SECRET_KEY`. No more default keys in the codebase.
- **Strict CORS:** Enforced origin restriction to prevent CSRF via `ALLOWED_ORIGINS`.
- **Input Sanitization:** Robust validation of IP, ports, and protocols to protect against command injections.
- **Time Machine:** Automated configuration snapshots before any rule changes.
- **Fail2Ban Integration:** Real-time monitoring and management of active bans.

## 🚀 Branches & Deployment Modes

| Branch | Mode | Description |
| :--- | :--- | :--- |
| `main` | **Docker** | Optimized for containers (Docker Compose). **Recommended.** |
| `classic` | **Bare Metal** | Direct installation on system via `systemd`. |

## 📦 Installation & Security Setup

### 1. `main` Branch (Docker) — Recommended

**Step 1: Clone and Prepare**
```bash
git clone https://github.com/weby-homelab/ufw-gui.git
cd ufw-gui
cp backend/.env.example backend/.env
```

**Step 2: Generate a Unique Secret Key**
For maximum security, generate a random key (at least 32 characters):
```bash
openssl rand -hex 32
```

**Step 3: Edit `.env`**
Open `backend/.env` and insert your generated key:
```env
UFW_GUI_SECRET_KEY=your_generated_key
ALLOWED_ORIGINS=https://your-domain.com,http://localhost:5173
```
> **WARNING:** If `UFW_GUI_SECRET_KEY` is not set, the container will exit with a `ValueError`. This prevents accidental use of insecure defaults.

**Step 4: Deploy**
```bash
docker compose up -d
```

### 2. `classic` Branch (Bare Metal)

**Step 1: Install Dependencies**
```bash
sudo apt update && sudo apt install ufw fail2ban python3-pip
cd backend
pip install -r requirements.txt
```

**Step 2: Setup Environment Variables (Systemd)**
Create a service file at `/etc/systemd/system/ufw-gui.service` and add:
```ini
[Service]
Environment="UFW_GUI_SECRET_KEY=your_super_long_secret_key"
Environment="ALLOWED_ORIGINS=http://localhost:3000"
ExecStart=/usr/bin/python3 /path/to/backend/main.py
```

## 🔐 Why This Matters
Version **v1.4.0** implements **Secure by Design** principles. By removing all fallback keys, we ensure that every administrator **must** create their own unique secret. This eliminates mass attacks on default configurations.

---
**✦ 2026 Weby Homelab ✦**
Made with ❤️ in Kyiv
