<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Українська версія">
  </a>
</p>

<br>

# UFW-GUI v1.2.0 [![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest) DOCKER Edition

<p align="center">
  <img src="https://img.shields.io/github/last-commit/weby-homelab/ufw-gui" alt="GitHub last commit">
  <img src="https://img.shields.io/github/license/weby-homelab/ufw-gui" alt="License">
  <img src="https://img.shields.io/badge/python-3.12+-blue.svg?logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Docker-2496ED?style=flat&logo=docker&logoColor=white" alt="Platform Docker">
</p>

**Сучасна веб-панель керування фаєрволом UFW для Debian/Ubuntu.**

Ця гілка (`main`) призначена для швидкого розгортання через **Docker Compose**. Усі сервіси (Nginx, Backend, Frontend) упаковані в контейнери для максимальної ізоляції.

---

## 🚀 Основні можливості v1.2.0

- **🔒 Hardened Security:** Повна ізоляція API, динамічна генерація JWT-секретів та сувора валідація вхідних даних (Regex).
- **📈 Статистика атак:** Візуалізація заблокованого трафіку за останні 24 години.
- **🕒 Машина часу (Snapshots):** Автоматичне створення снапшотів конфігурації UFW перед кожною зміною.
- **🛡 Safe Reload:** Режим тестування (60 секунд) для запобігання втрати доступу.
- **🤖 Fail2Ban Integration:** Відображення активних банів SSH та можливість розбану.

---

## 🐳 Швидкий запуск (Docker)

### 1. Клонування
```bash
git clone https://github.com/weby-homelab/ufw-gui.git
cd ufw-gui
```

### 2. Конфігурація
Створіть файл `.env` з вашим секретним ключем:
```bash
echo "UFW_GUI_SECRET_KEY=$(openssl rand -hex 32)" > .env
```

### 3. Запуск
```bash
docker compose up -d --build
```

Панель буде доступна на порті **80** (або іншому, налаштованому в `docker-compose.yml`).

---

## 🏗 Архітектура (Docker)

```mermaid
graph TD
    User[👤 Адмін] -->|Port 80| Nginx[🌐 Nginx Container]
    Nginx -->|Proxy| Frontend[📱 React Container]
    Nginx -->|Proxy /api| Backend[🐍 FastAPI Container]
    Backend -->|Host Access| UFW[🛡️ Host UFW]
```

## 📜 Ліцензія
Розповсюджується під ліцензією **MIT**.

<p align="center">
  ✦ 2026 Weby Homelab ✦<br>
  Made with ❤️ for Linux Security
</p>
