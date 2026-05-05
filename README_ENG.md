<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Українська версія">
  </a>
</p>

<br>

<h1 align="center">🛡️ UFW-GUI (Bare Metal Edition)</h1>

<p align="center">
  <a href="https://github.com/weby-homelab/ufw-gui/releases/latest"><img src="https://img.shields.io/github/v/release/weby-homelab/ufw-gui" alt="Latest Release"></a>
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/system-Debian_|_Ubuntu_|_AlmaLinux-red.svg" alt="System">
</p>

<p align="center">
  <strong>Modern, fast, and aesthetic network security management directly on your Linux host.</strong>
</p>

## ✨ Overview

**UFW-GUI** is a professional web panel for managing `UFW` and `Fail2Ban`. It transforms complex console commands into an intuitive dashboard with real-time analytics. Perfect for servers where using Docker is undesirable or impossible.

### 📸 App Interface

<p align="center">
  <img src="ufw-gui-1.png" width="80%" alt="UFW-GUI Dashboard" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <br>
  <em>Analytics and Security System Status</em>
</p>

<p align="center">
  <img src="ufw-gui-2.png" width="80%" alt="UFW-GUI Rule Management" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <br>
  <em>Intuitive Rule Management and Fail2Ban Integration</em>
</p>

## 🚀 Key Features

### 🛠 Rule Management
- **Quick Rules:** Quickly add allow or deny rules for ports and IPs.
- **Rule Management:** View and delete active rules directly through your browser.
- **Test Mode:** Safely test rules for 60 seconds with automatic rollback.

### 🔍 Threat Intelligence & Analytics
- **Live Drops:** Track dropped packets in real-time.
- **Visual Analytics:** Graphs showing attack activity over the last 24 hours.
- **Fail2Ban Control:** Full control over active bans and jail status.

### 🛡 Security & Reliability
- **Auto-Snapshots:** The system automatically creates a backup before every change.
- **Audit Logs:** Detailed activity log for team collaboration.
- **Telegram Alerts:** Instant notifications about rule changes sent to your Telegram.

---

## 🏗️ System Architecture

```mermaid
graph TD
    User((Admin)) -->|HTTPS| Nginx[Nginx Service]
    Nginx -->|Static| UI[Frontend: React Build]
    Nginx -->|Proxy| API[Backend: FastAPI]
    
    subgraph "Host OS"
        Nginx
        UI
        API
        UFW[UFW Engine]
        F2B[Fail2Ban]
    end
    
    API -->|Execute| UFW
    API -->|Control| F2B
    API -->|Persistence| DB[(SQLite / JSON)]
    API -->|Alerts| TG[Telegram Bot]

    style User fill:#f9f,stroke:#333,stroke-width:2px
    style Nginx fill:#f5f5f5,stroke:#6366f1,stroke-width:2px
```

---

## 📦 Installation (Brief)

Installing the Bare Metal version requires **Python 3**, **Node.js**, and **Nginx**.

1.  **Clone the repository:**
    ```bash
    git clone -b classic https://github.com/weby-homelab/ufw-gui.git /opt/ufw-gui
    ```

2.  **Configure backend:**
    ```bash
    cd /opt/ufw-gui/backend
    pip3 install -r requirements.txt
    ```

3.  **Build frontend:**
    ```bash
    cd /opt/ufw-gui/frontend
    npm install && npm run build
    ```

4.  **Setup services:**
    Use `systemd` to start the backend and `nginx` to serve static files.

---

## 📋 System Requirements
- **OS:** Ubuntu 22.04/24.04, Debian 11/12, AlmaLinux 9.
- **Dependencies:** `python3`, `nodejs`, `nginx`, `ufw`, `fail2ban`.
- **Access:** `root` (or `sudo`) permissions to manage system services.

---

<br>
<p align="center">
  Built in Ukraine under air raid sirens &amp; blackouts ⚡<br>
  &copy; 2026 Weby Homelab
</p>
