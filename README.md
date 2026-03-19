<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Українська версія">
  </a>
</p>

<br>

<p align="center">
  <img src="https://img.shields.io/github/v/release/weby-homelab/ufw-gui?style=for-the-badge&color=purple" alt="Latest Release">
  <img src="https://img.shields.io/badge/Branch-Main_(Docker)-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Branch Main">
</p>

# UFW-GUI: Docker Edition

**UFW-GUI** — це сучасна, легка та безпечна веб-панель для управління фаєрволом UFW у дистрибутивах Debian та Ubuntu. Проект створений для системних адміністраторів, які цінують візуальний контроль, безпеку та швидкість налаштування.

Гілка `main` призначена для швидкого розгортання через **Docker Compose**. Усі сервіси (Nginx, Backend, Frontend) упаковані в контейнери для максимальної ізоляції.

---

## 🛡️ Безпека та Функціонал

Професійний підхід до управління мережевим захистом:

*   **Safe Reload:** Механізм захисту від самоблокування (60-секундний тестовий режим з авто-відкатом).
*   **Time Machine:** Система автоматичних снапшотів конфігурації перед кожною зміною.
*   **Attack Analytics:** Інтерактивні графіки заблокованого трафіку за останні 24 години.
*   **Fail2Ban Integration:** Візуалізація та управління активними банами SSH (перегляд та розбан в один клік).
*   **Smart Alerts:** Миттєві Telegram-сповіщення про будь-які зміни в правилах або дії адміністраторів.
*   **Audit Trail:** Повна історія дій користувачів у вбудованому журналі аудиту.

---

## 🐳 Швидкий запуск (Docker)

## 🐳 Швидкий запуск (Docker)

Найпростіший спосіб запустити **UFW-GUI** — використовувати офіційний Docker-образ:

```bash
docker run -d \
  --name ufw-gui \
  --network host \
  --privileged \
  -v /etc/ufw:/etc/ufw \
  -v /var/run/fail2ban/fail2ban.sock:/var/run/fail2ban/fail2ban.sock \
  -v /var/log:/var/log:ro \
  webyhomelab/ufw-gui:latest
```

Або через **docker-compose.yml**:

```yaml
services:
  ufw-gui:
    image: webyhomelab/ufw-gui:latest
    container_name: ufw-gui
    network_mode: host
    privileged: true
    volumes:
      - /etc/ufw:/etc/ufw
      - /var/run/fail2ban/fail2ban.sock:/var/run/fail2ban/fail2ban.sock
      - /var/log:/var/log:ro
    restart: always
```

Панель буде доступна за адресою вашого сервера на порті **8080**. При першому вході система автоматично запропонує створити обліковий запис суперадміна.

---

## 🏗️ Архітектура рішення

Проект побудований як **All-in-One Docker Image**:

1.  **Frontend (React):** Швидкий та адаптивний SPA-інтерфейс, зібраний та вбудований у бекенд.
2.  **Backend (FastAPI):** Асинхронний API, який обслуговує запити та роздає статичні файли фронтенду.
3.  **OS Integration:** Прямий доступ до `ufw` та `fail2ban.sock` через `network: host` та `privileged` режим.

---

## 📜 Гілки та версії

*   `main` — **Docker Edition**. Рекомендовано для серверів з Docker-інфраструктурою.
*   `classic` — **Bare Metal**. Пряме розгортання в ОС через Systemd (без контейнерів).

---

## 🤝 Підтримка та Розробка

<p align="center">
  <img src="https://img.shields.io/github/last-commit/weby-homelab/ufw-gui" alt="GitHub last commit">
  <img src="https://img.shields.io/github/license/weby-homelab/ufw-gui" alt="License">
</p>

Розроблено з ❤️ командою **Weby Homelab** для спільноти Linux.
