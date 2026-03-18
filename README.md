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
  <img src="https://img.shields.io/badge/Branch-Classic_(Bare--Metal)-E4405F?style=for-the-badge&logo=linux&logoColor=white" alt="Branch Classic">
</p>

# UFW-GUI: Bare Metal Edition

**UFW-GUI** — це сучасна веб-панель для управління фаєрволом UFW, розроблена для прямого розгортання в операційній системі Debian або Ubuntu. Ця версія ідеально підходить для серверів, де використання Docker не є бажаним або можливим.

Гілка `classic` розгортається як набір системних сервісів (**Systemd**) під управлінням **Nginx**.

---

## 🛡️ Безпека та Функціонал

Професійний підхід до управління мережевим захистом:

*   **Safe Reload:** Механізм захисту від самоблокування (60-секундний тестовий режим з авто-відкатом).
*   **Time Machine:** Система автоматичних снапшотів конфігурації перед кожною зміною.
*   **Attack Analytics:** Інтерактивні графіки заблокованого трафіку за останні 24 години.
*   **Fail2Ban Integration:** Візуалізація та управління активними банами SSH.
*   **Smart Alerts:** Миттєві Telegram-сповіщення про дії адміністраторів.
*   **Audit Trail:** Детальна історія всіх змін у вбудованому журналі.

---

## 🛠️ Встановлення (Bare Metal)

### 1. Підготовка системи
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nodejs npm nginx ufw git
```

### 2. Клонування та Бекенд
```bash
git clone -b classic https://github.com/weby-homelab/ufw-gui.git
cd ufw-gui/backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 3. Збирання Фронтенду
```bash
cd ../frontend
npm install
npm run build
# Копіювання у веб-директорію
sudo mkdir -p /var/www/html/ufw-gui
sudo cp -r dist/* /var/www/html/ufw-gui/
sudo chown -R www-data:www-data /var/www/html/ufw-gui/
```

### 4. Налаштування Systemd
Створіть сервіс для бекенду:
```bash
sudo nano /etc/systemd/system/ufw-gui-backend.service
```
*(Детальні конфігурації сервісу та Nginx доступні у файлі INSTRUCTIONS.md цієї гілки).*

---

## 🏗️ Архітектура рішення

У цій версії всі компоненти працюють безпосередньо в середовищі хоста:

1.  **Frontend:** Статичні файли, що обслуговуються локальним Nginx.
2.  **Backend:** FastAPI додаток, що працює під управлінням Uvicorn як системний демон.
3.  **Security:** Пряма взаємодія з локальними утилітами `ufw` та `fail2ban`.

---

## 📜 Гілки та версії

*   `main` — **Docker Edition**. Рекомендовано для швидкого розгортання.
*   `classic` — **Bare Metal**. Пряме розгортання в ОС.

---

## 🤝 Підтримка та Розробка

<p align="center">
  <img src="https://img.shields.io/github/last-commit/weby-homelab/ufw-gui" alt="GitHub last commit">
  <img src="https://img.shields.io/github/license/weby-homelab/ufw-gui" alt="License">
</p>

Розроблено з ❤️ командою **Weby Homelab** для спільноти Linux.
