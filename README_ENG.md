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
  <img src="https://img.shields.io/badge/Branch-Classic_(Bare--Metal)-E4405F?style=for-the-badge&logo=linux&logoColor=white" alt="Branch Classic">
</p>

# UFW-GUI: Bare Metal Edition

**UFW-GUI** is a modern web interface for managing the UFW firewall, designed for direct deployment on Debian or Ubuntu operating systems. This version is ideal for servers where using Docker is not desired or possible.

The `classic` branch is deployed as a set of system services (**Systemd**) managed by **Nginx**.

---

## 🛡️ Security & Features

Professional approach to network protection management:

*   **Safe Reload:** Self-locking protection mechanism (60-second test mode with auto-rollback).
*   **Time Machine:** Automatic configuration snapshots system created before every change.
*   **Attack Analytics:** Interactive charts showing blocked traffic for the last 24 hours.
*   **Fail2Ban Integration:** Visualization and management of active SSH bans.
*   **Smart Alerts:** Instant Telegram notifications about administrative actions.
*   **Audit Trail:** Detailed history of all changes in the built-in log.

---

## 🛠️ Installation (Bare Metal)

### 1. System Preparation
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nodejs npm nginx ufw git
```

### 2. Cloning & Backend
```bash
git clone -b classic https://github.com/weby-homelab/ufw-gui.git
cd ufw-gui/backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 3. Frontend Build
```bash
cd ../frontend
npm install
npm run build
# Copy to web directory
sudo mkdir -p /var/www/html/ufw-gui
sudo cp -r dist/* /var/www/html/ufw-gui/
sudo chown -R www-data:www-data /var/www/html/ufw-gui/
```

### 4. Systemd Setup
Create a service for the backend:
```bash
sudo nano /etc/systemd/system/ufw-gui-backend.service
```
*(Detailed service and Nginx configurations are available in the INSTRUCTIONS.md file of this branch).*

---

## 🏗️ Architecture

In this version, all components run directly in the host environment:

1.  **Frontend:** Static files served by local Nginx.
2.  **Backend:** FastAPI application running under Uvicorn as a system daemon.
3.  **Security:** Direct interaction with local `ufw` and `fail2ban` utilities.

---

## 📜 Branches & Versions

*   `main` — **Docker Edition**. Recommended for quick deployment.
*   `classic` — **Bare Metal**. Direct OS deployment.

---

## 🤝 Support & Development

<p align="center">
  <img src="https://img.shields.io/github/last-commit/weby-homelab/ufw-gui" alt="GitHub last commit">
  <img src="https://img.shields.io/github/license/weby-homelab/ufw-gui" alt="License">
</p>

Developed with ❤️ by the **Weby Homelab** team for the Linux community.
