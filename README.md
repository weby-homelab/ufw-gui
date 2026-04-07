# 🛡️ UFW-GUI v1.4.0 — NETWORK SECURITY (Bare Metal Edition)

[![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest)

A modern, secure web interface for managing the **UFW** firewall on **Ubuntu/Debian** servers (Direct System Installation).

## 🛡️ Security Hardening (v1.4.0)
- **Zero-Fallback Secrets:** App requires a defined `UFW_GUI_SECRET_KEY` to start.
- **Strict CORS:** Enforced origin restriction via `ALLOWED_ORIGINS`.
- **Input Sanitization:** Robust validation of IP, ports, and protocols.

## 🛠️ Bare Metal Installation (Classic Mode)

1. **Install Dependencies:**
   ```bash
   sudo apt update && sudo apt install ufw fail2ban python3-pip
   ```

2. **Clone & Setup Environment:**
   ```bash
   git clone https://github.com/weby-homelab/ufw-gui.git
   cd ufw-gui/backend
   pip install -r requirements.txt
   ```

3. **Configure Systemd Service:**
   Create `/etc/systemd/system/ufw-gui.service`:
   ```ini
   [Service]
   Environment="UFW_GUI_SECRET_KEY=your_generated_secret"
   Environment="ALLOWED_ORIGINS=http://localhost:3000"
   ExecStart=/usr/bin/python3 /path/to/backend/main.py
   ```

---

# 🇺🇦 УКРАЇНСЬКА ВЕРСІЯ (BARE METAL)

## 🛡️ UFW-GUI v1.4.0 — МЕРЕЖЕВА БЕЗПЕКА

Веб-інтерфейс для керування **UFW** безпосередньо на вашій системі.

## 🛠️ Встановлення (Bare Metal)

1. **Встановіть системні пакунки:** `ufw`, `fail2ban`, `python3-pip`.
2. **Налаштуйте Python:** Встановіть бібліотеки з `requirements.txt`.
3. **Запустіть як сервіс:** Використовуйте `systemd` з обов’язковим вказанням `UFW_GUI_SECRET_KEY`.

---
**✦ 2026 Weby Homelab ✦**
