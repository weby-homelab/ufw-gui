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

---

## 🛡️ Security & Features

*   **All-in-One Docker Image:** Simple deployment with a single container.
*   **Safe Reload:** Self-locking protection mechanism (60-second test mode with auto-rollback).
*   **Time Machine:** Automatic configuration snapshots created before every change.
*   **Attack Analytics:** Interactive charts showing blocked traffic for the last 24 hours.
*   **Fail2Ban Integration:** Management of active bans (view and unban in one click).
*   **Smart Alerts:** Instant Telegram notifications about administrative actions.

---

## 🐳 Quick Start (Docker)

The fastest way to run **UFW-GUI** is using the official Docker image:

```bash
docker run -d \
  --name ufw-gui \
  --network host \
  --privileged \
  -v /etc/ufw:/etc/ufw \
  -v /var/run/fail2ban/fail2ban.sock:/var/run/fail2ban/fail2ban.sock \
  -v /var/log:/var/log:ro \
  webyhomelab/ufw-gui:latest
```

Or via **docker-compose.yml**:

```yaml
services:
  ufw-gui:
    image: webyhomelab/ufw-gui:latest
    container_name: ufw-gui
    network_mode: host
    privileged: true
    volumes:
      - /etc/ufw:/etc/ufw
      - /var/run/fail2ban/fail2ban.sock:/var/run/fail2ban/fail2ban.sock
      - /var/log:/var/log:ro
      - ./data:/app/data
    restart: always
```

The panel will be available on port **8080**.

---

## 🏗️ Architecture

The project is built as an **All-in-One Docker Image**:

1.  **Frontend (React):** Fast SPA interface built and embedded into the backend.
2.  **Backend (FastAPI):** Asynchronous API serving both requests and static files.
3.  **OS Integration:** Direct interaction with `ufw` and `fail2ban` via host networking.

---

## 🤝 Support & Development

Developed with ❤️ by the **Weby Homelab** team.
