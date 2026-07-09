FROM python:3.11-slim

WORKDIR /app

# FFmpeg + system dependencies required by Playwright's Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer-cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright's Chromium browser and its OS-level deps
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy only the application source
COPY app/ ./app/

# Output directory (override with a volume mount in production)
RUN mkdir -p output

EXPOSE 8000

CMD ["uvicorn", "app.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
