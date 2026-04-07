# 🛡️ UFW-GUI v1.4.0 — СВІТЛО⚡️ БЕЗПЕКА (Security Hardening Release)

[![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest)
[![Docker Pulls](https://img.shields.io/docker/pulls/webyhomelab/ufw-gui-backend)](https://hub.docker.com/r/webyhomelab/ufw-gui-backend)

Сучасний, швидкий та максимально безпечний веб-інтерфейс для керування брандмауером **UFW** на серверах Ubuntu/Debian.

## 🛡️ Що нового у v1.4.0 (Security Hardening)
- **Zero-Fallback Secrets:** Додаток більше не запускається без встановленого `UFW_GUI_SECRET_KEY`. Жодних дефолтних ключів у коді.
- **Strict CORS:** Повне обмеження доступу з невідомих доменів через `ALLOWED_ORIGINS`.
- **Input Sanitization:** Жорстка валідація IP, портів та протоколів для захисту від ін'єкцій.
- **Time Machine:** Автоматичні снапшоти конфігурації перед будь-якою зміною правил.
- **Fail2Ban Integration:** Керування активними банами в реальному часі.

## 🚀 Гілки та Режими

| Гілка | Режим | Опис |
| :--- | :--- | :--- |
| `main` | **Docker** | Оптимізовано для контейнерів (Docker Compose). **Рекомендовано.** |
| `classic` | **Bare Metal** | Пряма інсталяція на систему через `systemd`. |

## 📦 Встановлення та Налаштування Безпеки

### 1. Гілка `main` (Docker) — Рекомендовано

**Крок 1: Клонування та підготовка**
```bash
git clone https://github.com/weby-homelab/ufw-gui.git
cd ufw-gui
cp backend/.env.example backend/.env
```

**Крок 2: Генерація унікального секретного ключа**
Для максимальної безпеки згенеруйте випадковий ключ (мінімум 32 символи):
```bash
openssl rand -hex 32
```

**Крок 3: Редагування `.env`**
Відкрийте `backend/.env` та вставте згенерований ключ:
```env
UFW_GUI_SECRET_KEY=ваш_згенерований_ключ
ALLOWED_ORIGINS=https://vash-domen.com,http://localhost:5173
```
> **УВАГА:** Якщо `UFW_GUI_SECRET_KEY` не буде встановлено, контейнер видасть помилку `ValueError` і не запуститься. Це захищає вас від використання дефолтних паролів.

**Крок 4: Запуск**
```bash
docker compose up -d
```

### 2. Гілка `classic` (Bare Metal)

**Крок 1: Встановлення залежностей**
```bash
sudo apt update && sudo apt install ufw fail2ban python3-pip
cd backend
pip install -r requirements.txt
```

**Крок 2: Налаштування змінних оточення (Systemd)**
Створіть файл сервісу `/etc/systemd/system/ufw-gui.service` та додайте секцію `[Service]`:
```ini
[Service]
Environment="UFW_GUI_SECRET_KEY=ваш_довгий_секретний_ключ"
Environment="ALLOWED_ORIGINS=http://localhost:3000"
ExecStart=/usr/bin/python3 /path/to/backend/main.py
```

## 🔐 Чому це важливо?
Версія **v1.4.0** впроваджує принцип **Secure by Design**. Ми видалили всі "запасні" ключі з коду. Тепер кожен адміністратор **зобов'язаний** створити власний унікальний секрет. Це унеможливлює масові атаки на дефолтні конфігурації.

---
**✦ 2026 Weby Homelab ✦**
Made with ❤️ in Kyiv
