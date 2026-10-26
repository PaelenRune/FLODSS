# ==============================================================================
# FLODSS — Production Multi-Stage Dockerfile for 24/7 Cloud Hosting (Render, Railway, Fly.io)
# Single-Origin Deployment: Python 3.12 FastAPI + React Vite SPA
# ==============================================================================

# --- Stage 1: Build Frontend Single-Page App ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python Backend Runtime ---
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python production dependencies
COPY backend/requirements-prod.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements-prod.txt

# Copy backend application source
COPY backend/ ./backend/

# Copy initial data (and SQLite database if present)
COPY data/ ./data/

# Copy compiled frontend from Stage 1 into backend's expected single-origin path
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ensure data directory exists for SQLite
RUN mkdir -p /app/data

# Environment configuration
ENV PORT=8000 \
    HOST=0.0.0.0 \
    ENVIRONMENT=production \
    DATABASE_PATH=data/flodss_research.db \
    AUTH_ENFORCED=false \
    AI_ENABLED=false \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Start Uvicorn on dynamic cloud PORT (Render, Railway injects $PORT)
CMD ["sh", "-c", "uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
