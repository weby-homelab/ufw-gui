<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Українська версія">
  </a>
</p>

<br>

<h1 align="center">🛡️ UFW-GUI v1.4.0 — МЕРЕЖЕВА БЕЗПЕКА (Docker Edition)</h1>

<p align="center">
  <a href="https://github.com/weby-homelab/ufw-gui/releases/latest"><img src="https://img.shields.io/github/v/release/weby-homelab/ufw-gui" alt="Latest Release"></a>
  <a href="https://hub.docker.com/r/webyhomelab/ufw-gui-backend"><img src="https://img.shields.io/docker/pulls/webyhomelab/ufw-gui-backend" alt="Docker Pulls"></a>
</p>

<p align="center">
  <strong>Сучасний, інтуїтивно зрозумілий веб-інтерфейс для керування брандмауером Uncomplicated Firewall (UFW) через Docker.</strong>
</p>

## ✨ Огляд

**UFW-GUI** — це елегантне та безпечне рішення для моніторингу та управління правилами фаєрвола на ваших серверах. Завдяки сучасному дизайну та продуманому функціоналу, контроль мережевої безпеки стає простим як ніколи. 

### 📸 Інтерфейс додатку

<p align="center">
  <img src="ufw-gui-1.png" width="80%" alt="UFW-GUI Головна панель" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <br>
  <em>Інформаційна панель та статус системи</em>
</p>

<p align="center">
  <img src="ufw-gui-2.png" width="80%" alt="UFW-GUI Керування правилами" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <br>
  <em>Зручне управління правилами та профілями</em>
</p>

## 🚀 Основні можливості

- **💡 Сучасний UI/UX:** Інтуїтивний інтерфейс.
- **📊 Візуалізація статусу:** Миттєвий перегляд стану UFW та активних з'єднань.
- **🛡️ Легке керування правилами:** Додавання, видалення та редагування правил в один клік.
- **🔒 Посилена безпека:** Захист секретним ключем, строгий CORS та санітизація вводу.
- **🐳 Docker Edition:** Швидке та ізольоване розгортання через контейнери.

## 🛡️ Оновлення безпеки (v1.4.0)
- **Zero-Fallback Secrets:** Додаток більше не запускається без встановленого `UFW_GUI_SECRET_KEY`.
- **Strict CORS:** Повне обмеження доступу з невідомих доменів.
- **Input Sanitization:** Жорстка валідація для захисту від ін’єкцій.

## 📦 Встановлення (Docker Edition)

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

<br>
<p align="center">
  Built in Ukraine under air raid sirens &amp; blackouts ⚡<br>
  &copy; 2026 Weby Homelab
</p>
