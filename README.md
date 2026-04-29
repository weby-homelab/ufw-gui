<p align="center">
  <a href="README_ENG.md">
    <img src="https://img.shields.io/badge/🇬🇧_English-00D4FF?style=for-the-badge&logo=readme&logoColor=white" alt="English README">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇺🇦_Українська-FF4D00?style=for-the-badge&logo=readme&logoColor=white" alt="Українська версія">
  </a>
</p>

<br>

# 🛡️ UFW-GUI v1.4.0 — МЕРЕЖЕВА БЕЗПЕКА (Bare Metal Edition)

[![Latest Release](https://img.shields.io/github/v/release/weby-homelab/ufw-gui)](https://github.com/weby-homelab/ufw-gui/releases/latest)

Веб-інтерфейс для керування **UFW** безпосередньо на вашій системі.

## 🛡️ Оновлення безпеки (v1.4.0)
- **Zero-Fallback Secrets:** Додаток вимагає встановленого `UFW_GUI_SECRET_KEY`.
- **Strict CORS:** Обмеження доступу через `ALLOWED_ORIGINS`.
- **Input Sanitization:** Жорстка валідація даних.

## 🛠️ Встановлення (Bare Metal)

1. **Встановіть залежності:**
   ```bash
   sudo apt update && sudo apt install ufw fail2ban python3-pip
   ```

2. **Налаштуйте Python:**
   ```bash
   git clone https://github.com/weby-homelab/ufw-gui.git
   cd ufw-gui/backend
   pip install -r requirements.txt
   ```

3. **Запустіть як сервіс:** Використовуйте `systemd` з обов’язковим вказанням `UFW_GUI_SECRET_KEY`.

---

<br>
<p align="center">
  Built in Ukraine under air raid sirens &amp; blackouts ⚡<br>
  &copy; 2026 Weby Homelab
</p>
