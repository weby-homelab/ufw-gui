<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Ukrainian version">
  </a>
</p>

<br>

<p align="center">
  <img src="https://img.shields.io/github/v/release/weby-homelab/ufw-gui?style=for-the-badge&color=purple" alt="Latest Release">
  <img src="https://img.shields.io/badge/Branch-Main_(Docker)-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Branch Main">
</p>

# UFW-GUI: Docker Edition

**UFW-GUI** is a modern, lightweight, and secure web interface for managing the UFW firewall on Debian and Ubuntu distributions. This project is built for system administrators who value visual control, security, and deployment speed.

The `main` branch is designed for quick deployment through **Docker Compose**. All services (Nginx, Backend, Frontend) are packaged in containers for maximum isolation.

---

## 🛡️ Security & Features

Professional approach to network protection management:

*   **Safe Reload:** Self-locking protection mechanism (60-second test mode with auto-rollback).
*   **Time Machine:** Automatic configuration snapshots system created before every change.
*   **Attack Analytics:** Interactive charts showing blocked traffic for the last 24 hours.
*   **Fail2Ban Integration:** Visualization and management of active SSH bans (view and unban in one click).
*   **Smart Alerts:** Instant Telegram notifications about any rule changes or administrative actions.
*   **Audit Trail:** Complete history of user actions in the built-in audit log.

---

## 🐳 Quick Start (Docker)

### 1. Clone the repository
```bash
git clone https://github.com/weby-homelab/ufw-gui.git
cd ufw-gui
```

### 2. Environment Configuration
Generate a unique secret key for JWT authorization:
```bash
echo "UFW_GUI_SECRET_KEY=$(openssl rand -hex 32)" > .env
```

### 3. Start Services
```bash
docker compose up -d --build
```

The panel will be available at your server's address on port **80**. On the first login, the system will automatically prompt you to create a superadmin account.

---

## 🏗️ Architecture

The project is split into three isolated layers:

1.  **Frontend (React):** Fast and responsive SPA interface.
2.  **Backend (FastAPI):** Asynchronous API with a high level of protection and validation.
3.  **Reverse Proxy (Nginx):** Provides secure proxying and static file serving.

---

## 📜 Branches & Versions

*   `main` — **Docker Edition**. Recommended for servers with Docker infrastructure.
*   `classic` — **Bare Metal**. Direct OS deployment via Systemd (no containers).

---

## 🤝 Support & Development

<p align="center">
  <img src="https://img.shields.io/github/last-commit/weby-homelab/ufw-gui" alt="GitHub last commit">
  <img src="https://img.shields.io/github/license/weby-homelab/ufw-gui" alt="License">
</p>

Developed with ❤️ by the **Weby Homelab** team for the Linux community.
