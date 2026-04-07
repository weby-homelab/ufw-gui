# 🛡️ UFW-GUI v1.4.0 — NETWORK SECURITY (Security Hardening Release)

[![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest)
[![Docker Pulls](https://img.shields.io/docker/pulls/webyhomelab/ufw-gui-backend)](https://hub.docker.com/r/webyhomelab/ufw-gui-backend)

A modern, fast, and secure web interface for managing the **UFW** firewall via **Docker**.

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

2. **Generate Secret:**
   ```bash
   openssl rand -hex 32
   ```

3. **Configure `.env`:**
   Insert your key and allowed domains:
   ```env
   UFW_GUI_SECRET_KEY=your_generated_key
   ALLOWED_ORIGINS=https://your-domain.com
   ```

4. **Deploy:**
   ```bash
   docker compose up -d
   ```

---

# 🇺🇦 УКРАЇНСЬКА ВЕРСІЯ (DOCKER)

## 🛡️ UFW-GUI v1.4.0 — МЕРЕЖЕВА БЕЗПЕКА

Сучасний веб-інтерфейс для керування **UFW** через **Docker**.

## 📦 Встановлення (Docker)

1. **Клонуйте та налаштуйте:**
   ```bash
   git clone https://github.com/weby-homelab/ufw-gui.git
   cd ufw-gui
   cp backend/.env.example backend/.env
   ```

2. **Згенеруйте секрет:** `openssl rand -hex 32`

3. **Відредагуйте `.env`:** Вставте ключ у `UFW_GUI_SECRET_KEY`.

4. **Запустіть:** `docker compose up -d`

---
**✦ 2026 Weby Homelab ✦**
