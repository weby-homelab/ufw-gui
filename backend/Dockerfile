FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ufw \
    fail2ban \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY VERSION .

ENV TZ=Europe/Kyiv
ENV UFW_GUI_SECRET_KEY=""
ENV ALLOWED_ORIGINS=""

# UFW requires privileged mode and access to /etc/ufw
VOLUME ["/etc/ufw", "/var/lib/ufw", "/var/log", "/var/run/fail2ban"]

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
