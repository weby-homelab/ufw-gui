<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Українська версія">
  </a>
</p>

<br>

# UFW-GUI v1.2.0 [![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest) DOCKER Edition

<p align="center">
  <img src="https://img.shields.io/github/last-commit/weby-homelab/ufw-gui" alt="GitHub last commit">
  <img src="https://img.shields.io/github/license/weby-homelab/ufw-gui" alt="License">
  <img src="https://img.shields.io/badge/python-3.12+-blue.svg?logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Docker-2496ED?style=flat&logo=docker&logoColor=white" alt="Platform Docker">
</p>

**A modern web interface for managing the UFW firewall on Debian/Ubuntu systems.**

This branch (`main`) is designed for quick deployment via **Docker Compose**. All services (Nginx, Backend, Frontend) are containerized for maximum isolation.

---

## 🚀 Key Features v1.2.0

- **🔒 Hardened Security:** Complete API isolation, dynamic JWT secret generation, and strict input validation (Regex).
- **📈 Attack Statistics:** Visualized charts of blocked requests from the last 24 hours.
- **🕒 Time Machine (Snapshots):** Automatic UFW configuration snapshots before every change.
- **🛡 Safe Reload:** Testing mode (60 seconds) to prevent losing connection to your server.
- **🤖 Fail2Ban Integration:** View active SSH bans and instantly unban IPs.

---

## 🐳 Quick Start (Docker)

### 1. Cloning
```bash
git clone https://github.com/weby-homelab/ufw-gui.git
cd ufw-gui
```

### 2. Configuration
Create a `.env` file with your secure key:
```bash
echo "UFW_GUI_SECRET_KEY=$(openssl rand -hex 32)" > .env
```

### 3. Launch
```bash
docker compose up -d --build
```

The panel will be available on port **80** (or as configured in `docker-compose.yml`).

---

## 🏗 Architecture (Docker)

```mermaid
graph TD
    User[👤 Admin] -->|Port 80| Nginx[🌐 Nginx Container]
    Nginx -->|Proxy| Frontend[📱 React Container]
    Nginx -->|Proxy /api| Backend[🐍 FastAPI Container]
    Backend -->|Host Access| UFW[🛡️ Host UFW]
```

## 📜 License
Distributed under the **MIT** License.

<p align="center">
  ✦ 2026 Weby Homelab ✦<br>
  Made with ❤️ for Linux Security
</p>
