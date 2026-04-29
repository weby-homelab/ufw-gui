<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Українська версія">
  </a>
</p>

<br>

# 🛡️ UFW-GUI v1.4.0 — NETWORK SECURITY (Bare Metal Edition)

[![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest)

A modern, secure web interface for managing the **UFW** firewall on **Ubuntu/Debian** servers.

## 🛡️ Security Hardening (v1.4.0)
- **Zero-Fallback Secrets:** App requires a defined `UFW_GUI_SECRET_KEY` to start.
- **Strict CORS:** Enforced origin restriction via `ALLOWED_ORIGINS`.
- **Input Sanitization:** Robust validation of IP, ports, and protocols.

## 🛠️ Bare Metal Installation (Classic Mode)

1. **Install Dependencies:**
   ```bash
   sudo apt update && sudo apt install ufw fail2ban python3-pip
   ```

2. **Clone & Setup:**
   ```bash
   git clone https://github.com/weby-homelab/ufw-gui.git
   cd ufw-gui/backend
   pip install -r requirements.txt
   ```

3. **Configure Systemd:**
   Create service file with `UFW_GUI_SECRET_KEY` and `ALLOWED_ORIGINS` env variables.

---

<br>
<p align="center">
  Built in Ukraine under air raid sirens &amp; blackouts ⚡<br>
  &copy; 2026 Weby Homelab
</p>
