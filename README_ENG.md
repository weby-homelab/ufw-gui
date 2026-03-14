<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Ukrainian version">
  </a>
</p>

<br>

# 🛡️ UFW-GUI (Weby Homelab)
*Lightweight, Fast, and Minimalistic UFW Management.*

[![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![System](https://img.shields.io/badge/system-Debian_|_Ubuntu-orange.svg)]()

**UFW-GUI** is a minimalistic web dashboard for managing `UFW` (Uncomplicated Firewall) and `Fail2Ban`. It's designed for projects where complex Firewalld zones aren't needed, but configuration speed and rule visibility are paramount. The perfect choice for personal servers and lightweight VPS.

---

## 🧩 System Architecture

```mermaid
graph TD
    User((Administrator)) -->|HTTPS / PWA| UI[Web Dashboard]
    
    subgraph "UFW-GUI Backend"
        UI -->|REST API| FastAPI[FastAPI Service]
        FastAPI -->|Exec| UFW[UFW Engine]
        FastAPI -->|Exec| F2B[Fail2Ban Client]
    end

    subgraph "Operating System"
        UFW -->|Apply Rules| IPT[iptables / nftables]
        F2B -->|Block IPs| IPT
    end

    FastAPI -->|Storage| JSON[(users.json)]
```

---

## ✨ Key Features

- **⚡ Mobile Interface:** Manage server security directly from your smartphone. Responsive design allows you to quickly open or close a port "on the go."
- **🧱 Simplified Rule Management:** Add and remove permissions in seconds. No complex configuration files.
- **🚫 Fail2Ban Monitoring:** View the list of blocked IPs and unban them in one click.
- **🔒 Security First:** Built-in Brute Force protection for the dashboard itself and JWT-based authorization.
- **🐳 Docker Ready:** Full support for Docker deployment to isolate the environment.

---

## 🛠️ Quick Start

### Via Docker Compose
```yaml
services:
  ufw-gui:
    image: webyhomelab/ufw-gui:latest
    container_name: ufw-gui
    privileged: true
    network_mode: host
    restart: unless-stopped
    env_file: .env
```
*Note: `privileged: true` and `network_mode: host` are mandatory for interacting with the host system's UFW.*

---

## 📋 System Requirements
- **OS:** Debian 11/12, Ubuntu 20.04/22.04/24.04.
- **Dependencies:** `ufw`, `fail2ban` (optional).
- **Access:** `root` privileges.

---
<p align="center">
  Made with ❤️ in Kyiv under air raid sirens and blackouts<br>
  <strong>✦ 2026 Weby Homelab ✦</strong>
</p>
