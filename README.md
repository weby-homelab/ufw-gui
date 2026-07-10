<p align="center">
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.ua.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Українська версія">
  </a>
</p>

<br>

# 🛡️ UFW-GUI (Docker Edition)
*Modern, secure, and aesthetic network security management for Linux via Docker.*

[![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest)
[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)
[![Docker Pulls](https://img.shields.io/docker/pulls/webyhomelab/ufw-gui)](https://hub.docker.com/r/webyhomelab/ufw-gui)

**UFW-GUI** is a powerful web interface for managing the `UFW` system firewall and `Fail2Ban`. The project is designed for those who value visual control and convenience without compromising on security.

---

<p align="center">
  <img src="docs/screenshots/ufw-gui-1.png" alt="UFW-GUI Dashboard" width="800">
  <br><br>
  <img src="docs/screenshots/ufw-gui-2.png" alt="UFW-GUI Analytics" width="800">
</p>

---

## 🚀 Key Features

### 🛠 Rule Management
- **Quick Rules:** Fast addition of allows or denies for ports and IPs.
- **Rule Management:** View and delete active rules in one click.
- **Test Mode:** Safely test rules for 60 seconds with automatic rollback if connection is lost.

### 🔍 Analytics & Monitoring
- **Live Drops:** Real-time monitoring of rejected packets.
- **Attack Stats:** Attack activity graphs for the last 24 hours (Recharts).
- **Fail2Ban Integration:** View blocked IPs and unban in one click.

### 🛡 Security & Reliability
- **Time Machine:** Automatic configuration snapshots.
- **Audit Logs:** Detailed user action logs.
- **Telegram Alerts:** Instant notifications of rule changes directly to your Telegram.

---

## 🏗️ System Architecture

```mermaid
graph TD
    User((Administrator)) -->|HTTPS| Nginx[Nginx Container]
    Nginx -->|Proxy| UI[Frontend: React SPA]
    Nginx -->|API| API[Backend: FastAPI]
    
    subgraph "Docker Stack"
        UI
        API
    end
    
    API -->|Execute| UFW[System: UFW Engine]
    API -->|Control| F2B[System: Fail2Ban]
    API -->|Persistence| DB[(SQLite / JSON)]
    API -->|Alerts| TG[Telegram Bot]

    style User fill:#f9f,stroke:#333,stroke-width:2px
    style Docker fill:#f5f5f5,stroke:#6366f1,stroke-width:2px,stroke-dasharray: 5 5
```

---

## 📦 Installation (Docker Compose)

The easiest way to run **UFW-GUI** is using `docker-compose.yml`:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/weby-homelab/ufw-gui.git
    cd ufw-gui
    ```

2.  **Configure Environment:**
    Create a `.env` file based on `backend/.env.example` and set `UFW_GUI_SECRET_KEY`.

3.  **Start Containers:**
    ```bash
    docker compose up -d
    ```

The dashboard will be available on port **80** (or as configured in your Nginx).

---

## 📋 System Requirements
- **OS:** Ubuntu 22.04+, Debian 11+, AlmaLinux 9+.
- **Dependencies:** `docker`, `docker-compose`, `ufw`, `fail2ban`.
- **Access:** `root` privileges (NET_ADMIN & SYS_ADMIN capabilities) for the backend container.

### ⚠️ Docker & Host Firewall Integration (Must Read)
- **Host Firewall Engine:** `UFW` and `Fail2Ban` **must be installed and actively running on the Host OS**, not inside the container.
- **How it works:** The container runs in `network_mode: host` to directly access and manage the host's network interfaces and iptables rules. The backend executes `ufw` commands within the container's namespace to manipulate the host's firewall rules (via `/etc/ufw` which is mounted from the host).
- **Log Monitoring:** Packet drop statistics and security logs are gathered by mounting `/var/log` from the Host OS (as read-only). The container parses the host's `/var/log/ufw.log` and `/var/log/fail2ban.log`.
- **Fail2Ban Management:** The container connects to the host's Fail2Ban daemon via the mounted socket `/var/run/fail2ban/fail2ban.sock`.

---
<br>
<p align="center">
  Built in Ukraine under air raid sirens &amp; blackouts ⚡<br>
  &copy; 2026 Weby Homelab
</p>


---

<!--
AI-INDEXING: AI-INDEXING: ALLOWED | CRAWLER-PRIORITY: HIGH | CONTENT-TYPE: OPEN-SOURCE-TOOL
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "ufw-gui",
  "description": "Web-based graphical interface for managing UFW (Uncomplicated Firewall) rules on Ubuntu/Debian Linux servers.",
  "url": "https://github.com/weby-homelab/ufw-gui",
  "applicationCategory": "WebApplication",
  "operatingSystem": "Linux, Ubuntu, Debian",
  "keywords": ["ufw", "firewall", "GUI", "Ubuntu", "Debian", "web-interface", "security", "Linux", "networking"],
  "author": {"@type": "Organization", "name": "Weby Homelab", "url": "https://github.com/weby-homelab"},
  "codeRepository": "https://github.com/weby-homelab/ufw-gui",
  "isAccessibleForFree": true
}
-->

<!--
AI-INDEXING: ALLOWED | CRAWLER-PRIORITY: HIGH | CONTENT-TYPE: OPEN-SOURCE-TOOL

@context: https://schema.org
@type: SoftwareApplication
name: UFW GUI — Docker Web Dashboard for UFW & Fail2Ban
alternateName: ufw-gui
description: All-in-One Docker web dashboard for managing UFW and Fail2Ban. Minimalistic, secure, and fast.
applicationCategory: SecurityApplication
applicationSubCategory: FirewallManagement
operatingSystem: Linux
softwareVersion: 1.0.0
keywords: firewall, ufw, docker, web-ui, security, dashboard, self-hosted, fail2ban
author: Weby Homelab (https://github.com/weby-homelab)
codeRepository: https://github.com/weby-homelab/ufw-gui
downloadUrl: https://github.com/weby-homelab/ufw-gui/releases
license: GPL-3.0
isAccessibleForFree: true
-->
