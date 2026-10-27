# --- Stage 1: Build React Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps --ignore-scripts
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Final Image ---
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies (ufw, fail2ban)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ufw \
    iptables \
    fail2ban \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Copy backend
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ ./backend/

# Copy built frontend to backend static directory
COPY --from=frontend-builder /app/frontend/dist /app/static

EXPOSE 8080

ENV TZ=Europe/Kyiv
ENV DATA_DIR=/app/data

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; port = os.getenv('PORT', '8080'); urllib.request.urlopen(f'http://localhost:{port}/api/health')" || exit 1

# Run FastAPI
CMD ["sh", "-c", "exec uvicorn backend.main:app --host \"${UFW_GUI_BIND_ADDRESS:-127.0.0.1}\" --port \"${PORT:-8080}\""]
