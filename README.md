<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Українська версія">
  </a>
</p>

<br>

# 🛡️ UFW-GUI v1.4.0 — МЕРЕЖЕВА БЕЗПЕКА (Docker Edition)

[![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest)
[![Docker Pulls](https://img.shields.io/docker/pulls/webyhomelab/ufw-gui-backend)](https://hub.docker.com/r/webyhomelab/ufw-gui-backend)

Сучасний веб-інтерфейс для керування **UFW** через **Docker**.

## 🛡️ Оновлення безпеки (v1.4.0)
- **Zero-Fallback Secrets:** Додаток більше не запускається без встановленого `UFW_GUI_SECRET_KEY`.
- **Strict CORS:** Повне обмеження доступу з невідомих доменів.
- **Input Sanitization:** Жорстка валідація для захисту від ін’єкцій.

## 📦 Встановлення (Docker)

1. **Клонуйте та налаштуйте:**
   ```bash
   git clone https://github.com/weby-homelab/ufw-gui.git
   cd ufw-gui
   cp backend/.env.example backend/.env
   ```

2. **Згенеруйте секрет:** `openssl rand -hex 32`

3. **Відредагуйте `.env`:** Вставте ключ у `UFW_GUI_SECRET_KEY` та налаштуйте `ALLOWED_ORIGINS`.

4. **Запустіть:** `docker compose up -d`

---
<p align="center">
  Made with ❤️ in Kyiv under air raid sirens and blackouts<br>
  <strong>© 2026 Weby Homelab</strong>
</p>
