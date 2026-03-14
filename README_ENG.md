<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Українська версія">
  </a>
</p>

<br>

# 🛡️ UFW-GUI (Weby Homelab)

**UFW-GUI** is a lightweight, fast, and secure web dashboard for managing the `UFW` (Uncomplicated Firewall) and `Fail2Ban` system on Debian and Ubuntu servers.

This project is designed as a minimalistic alternative for systems that do not require complex Firewalld zones, prioritizing speed, clarity, and reliability.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![OS](https://img.shields.io/badge/os-Debian%20%7C%20Ubuntu-orange.svg)
![Python](https://img.shields.io/badge/python-3.12-green.svg)

---

## ✨ Key Features

- ✅ **Simple Rule Management**: Add and remove `allow/deny` rules in seconds.
- 🌐 **Subnet Support**: Configure rules for specific IP addresses or entire ranges (CIDR).
- 📊 **Live Logs & Stats**: Real-time dropped packet monitoring and a detailed attack graph (10-minute intervals).
- 🚫 **Quick Ban**: Instantly block attacking IPs directly from the logs.
- 🛡️ **Fail2Ban Integration**: View active bans and manage them.
- 🕰️ **Time Machine**: Automatic configuration backups of `/etc/ufw` before every change.
- ⚡ **Test Rule (60s)**: Safely apply rules with an automatic rollback if you lose connection to the server.
- 👮 **Multi-User & Audit**: Role-based access and a detailed admin activity log.
- 🎨 **Theme Switcher**: Support for dark (Dark Glass) and light (Light Minimal) themes.
- 📱 **Mobile Ready**: Fully responsive design for managing your server from a smartphone.

---

## 🚀 Installation (Docker Compose)

### Prerequisites
- OS: Debian 11/12/13 or Ubuntu 22.04/24.04
- Installed: `docker`, `docker-compose-plugin`, `ufw`, `fail2ban`

### Setup
1. Clone the repository:
```bash
git clone https://github.com/weby-homelab/ufw-gui.git
cd ufw-gui
```
2. Start services:
```bash
docker compose up -d --build
```
3. Open the dashboard in your browser (port 80) and complete the **Initial Setup** to create the first superadmin.

---

## 🔒 Security First
- **Protected Ports**: The panel automatically blocks the deletion of rules for ports 22, 55222, 80, and 443 to ensure you never lose access.
- **Smart Whitelist**: Add your IP to the whitelist, and the system will ignore any attempts to ban your address.

---

## 📄 License
© 2026 Weby Homelab. All rights reserved. Developed for the Debian/Ubuntu community.