# --- Stage 1: Build React Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Final Image ---
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies (UFW, iptables, fail2ban)
RUN apt-get update && apt-get install -y \
    ufw \
    iptables \
    fail2ban \
    systemd \
    && rm -rf /var/lib/apt/lists/*

# Copy backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

# Copy built frontend to backend static directory
COPY --from=frontend-builder /app/frontend/dist /app/static

EXPOSE 8080

ENV TZ=Europe/Kyiv
ENV DATA_DIR=/app/data

# Run FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
