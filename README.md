# UFW-GUI v1.4.0 — СВІТЛО⚡️ БЕЗПЕКА (Security Hardening Release)

[![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest)
[![Docker Pulls](https://img.shields.io/docker/pulls/webyhomelab/ufw-gui-backend)](https://hub.docker.com/r/webyhomelab/ufw-gui-backend)

Сучасний, швидкий та максимально безпечний веб-інтерфейс для керування брандмауером **UFW** на серверах Ubuntu/Debian.

## 🛡️ Що нового у v1.4.0 (Security Hardening)
- **Zero-Fallback Secrets:** Додаток більше не запускається без встановленого `UFW_GUI_SECRET_KEY`. Жодних дефолтних ключів у коді.
- **Strict CORS:** Повне обмеження доступу з невідомих доменів.
- **Input Sanitization:** Жорстка валідація IP, портів та протоколів для захисту від ін'єкцій.
- **Time Machine:** Автоматичні снапшоти конфігурації перед будь-якою зміною правил.
- **Fail2Ban Integration:** Перегляд та керування активними банами в реальному часі.

## 🚀 Гілки та Режими

| Гілка | Режим | Опис |
| :--- | :--- | :--- |
| `main` | **Docker** | Оптимізовано для контейнерів (Docker Compose). |
| `classic` | **Bare Metal** | Пряма інсталяція на систему через `systemd`. |

## 📦 Встановлення (Docker - Гілка `main`)

1. **Клонуйте репозиторій:**
   ```bash
   git clone https://github.com/weby-homelab/ufw-gui.git
   cd ufw-gui
   ```

2. **Налаштуйте секрети:**
   ```bash
   cp backend/.env.example backend/.env
   # ОБОВ'ЯЗКОВО змініть SECRET_KEY
   nano backend/.env
   ```

3. **Запустіть:**
   ```bash
   docker compose up -d
   ```

## 🛠️ Встановлення (Bare Metal - Гілка `classic`)

1. **Встановіть залежності:**
   ```bash
   sudo apt update && sudo apt install ufw fail2ban python3-pip
   ```

2. **Налаштуйте Python середовище:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Запустіть сервіс:**
   ```bash
   export UFW_GUI_SECRET_KEY="your-super-long-secret"
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

---
**✦ 2026 Weby Homelab ✦**
Made with ❤️ in Kyiv
