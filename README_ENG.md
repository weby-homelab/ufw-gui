<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Українська версія">
  </a>
</p>

<br>

<h1 align="center">🛡️ UFW-GUI v1.4.0 — NETWORK SECURITY (Docker Edition)</h1>

<p align="center">
  <a href="https://github.com/weby-homelab/ufw-gui/releases/latest"><img src="https://img.shields.io/github/v/release/weby-homelab/ufw-gui" alt="Latest Release"></a>
  <a href="https://hub.docker.com/r/webyhomelab/ufw-gui-backend"><img src="https://img.shields.io/docker/pulls/webyhomelab/ufw-gui-backend" alt="Docker Pulls"></a>
</p>

<p align="center">
  <strong>A modern, secure web interface for managing the Uncomplicated Firewall (UFW) via Docker.</strong>
</p>

## ✨ Overview

**UFW-GUI** is an elegant and secure solution for monitoring and managing firewall rules on your servers. With its modern design and thoughtful functionality, network security control has never been easier.

### 📸 App Interface

<p align="center">
  <img src="ufw-gui-1.png" width="80%" alt="UFW-GUI Main Dashboard" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <br>
  <em>Dashboard and System Status</em>
</p>

<p align="center">
  <img src="ufw-gui-2.png" width="80%" alt="UFW-GUI Rule Management" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <br>
  <em>Easy Rule Management and Profiles</em>
</p>

## 🚀 Key Features

- **💡 Modern UI/UX:** Intuitive interface.
- **📊 Status Visualization:** Instant overview of UFW state and active connections.
- **🛡️ Easy Rule Management:** Add, delete, and edit rules in one click.
- **🔒 Hardened Security:** Secret key protection, strict CORS, and input sanitization.
- **🐳 Docker Edition:** Fast and isolated deployment via containers.

## 🛡️ Security Hardening (v1.4.0)
- **Zero-Fallback Secrets:** App requires a defined `UFW_GUI_SECRET_KEY` to start.
- **Strict CORS:** Enforced origin restriction via `ALLOWED_ORIGINS`.
- **Input Sanitization:** Robust validation of IP, ports, and protocols.

## 📦 Docker Installation (Main Mode)

1. **Clone & Setup:**
   ```bash
   git clone https://github.com/weby-homelab/ufw-gui.git
   cd ufw-gui
   cp backend/.env.example backend/.env
   ```

2. **Generate Secret:** `openssl rand -hex 32`

3. **Configure `.env`:** Insert your generated key and allowed domains.

4. **Deploy:** `docker compose up -d`

---

<br>
<p align="center">
  Built in Ukraine under air raid sirens &amp; blackouts ⚡<br>
  &copy; 2026 Weby Homelab
</p>
