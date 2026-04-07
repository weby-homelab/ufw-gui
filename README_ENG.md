# UFW-GUI v1.4.0 — LIGHT⚡️ SAFETY (Security Hardening Release)

[![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest)
[![Docker Pulls](https://img.shields.io/docker/pulls/webyhomelab/ufw-gui-backend)](https://hub.docker.com/r/webyhomelab/ufw-gui-backend)

A modern, fast, and secure web interface for managing the **UFW** firewall on Ubuntu/Debian servers.

## 🛡️ What's New in v1.4.0 (Security Hardening)
- **Zero-Fallback Secrets:** The app will not start without a defined `UFW_GUI_SECRET_KEY`. No more default keys in code.
- **Strict CORS:** Enforced origin restriction to prevent CSRF.
- **Input Sanitization:** Robust validation of IP, ports, and protocols to protect against command injections.
- **Time Machine:** Automated configuration snapshots before any rule changes.
- **Fail2Ban Integration:** Real-time monitoring and management of active bans.

## 🚀 Branches & Deployment Modes

| Branch | Mode | Description |
| :--- | :--- | :--- |
| `main` | **Docker** | Optimized for containers (Docker Compose). |
| `classic` | **Bare Metal** | Direct installation on system via `systemd`. |

## 📦 Installation (Docker - `main` branch)

1. **Clone Repository:**
   ```bash
   git clone https://github.com/weby-homelab/ufw-gui.git
   cd ufw-gui
   ```

2. **Configure Secrets:**
   ```bash
   cp backend/.env.example backend/.env
   # MANDATORY: Change SECRET_KEY
   nano backend/.env
   ```

3. **Deploy:**
   ```bash
   docker compose up -d
   ```

## 🛠️ Installation (Bare Metal - `classic` branch)

1. **Install Dependencies:**
   ```bash
   sudo apt update && sudo apt install ufw fail2ban python3-pip
   ```

2. **Configure Python Environment:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Run Service:**
   ```bash
   export UFW_GUI_SECRET_KEY="your-super-long-secret"
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

---
**✦ 2026 Weby Homelab ✦**
Made with ❤️ in Kyiv
