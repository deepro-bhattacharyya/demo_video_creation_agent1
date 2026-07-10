# Stage 1: Build the React frontend
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend (includes the built frontend)
FROM python:3.11-slim
WORKDIR /app

# FFmpeg + system dependencies required by Playwright's Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright: Chromium browser + its OS-level deps
RUN playwright install chromium
RUN playwright install-deps chromium

# Application source
COPY app/ ./app/

# React build — served by FastAPI's StaticFiles at runtime
COPY --from=frontend-build /frontend/dist ./frontend/dist

# Output directory (mount a host volume in production to persist videos)
RUN mkdir -p output

EXPOSE 8000

CMD ["uvicorn", "app.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
