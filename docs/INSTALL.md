# Installation & Setup Guide

## Prerequisites

Make sure the following are installed on your machine before proceeding.

| Requirement | Minimum version | Install |
|-------------|----------------|---------|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| FFmpeg | any recent | See below |
| Git | any | [git-scm.com](https://git-scm.com/) |

### Installing FFmpeg

FFmpeg is a system dependency — it is **not** a pip package.

**Windows (manual — no admin or package manager required)**

1. Go to **[https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)** (the official Windows builds linked from ffmpeg.org).
2. Under **"release builds"**, download `ffmpeg-release-essentials.zip`.
3. Extract the zip — you'll get a folder like `ffmpeg-7.x-essentials_build\`.
4. Move (or copy) that folder somewhere permanent, e.g. `C:\tools\ffmpeg\`.
5. Add the `bin` subfolder to your user `PATH`:
   - Open **Start → "Edit environment variables for your account"**
   - Select **Path** → **Edit** → **New**
   - Paste `C:\tools\ffmpeg\bin` (adjust if you chose a different location)
   - Click **OK** on all dialogs, then **restart your terminal**.

**macOS**
```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu)**
```bash
sudo apt update && sudo apt install ffmpeg
```

Verify the install:
```bash
ffmpeg -version
```

---

## 1. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows (PowerShell)**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

---

## 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Install Playwright browsers

```bash
playwright install chromium
```

This downloads the Chromium browser binary used for login and screen recording.

---

## 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in the values:

```env
# Gemini API key — used for both script generation and TTS voice-over
GEMINI_API_KEY=your-key-here

# AgenticQEAHub platform
AGENTICQEAHUB_BASE_URL=https://your-platform-host
HUB_EMAIL=your-login-email
HUB_PASSWORD=your-login-password

# Where finished videos are written (default is fine locally)
OUTPUT_DIR=./output
```

> **Never commit `.env`.** It is already listed in `.gitignore`.
> Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

---

## 5. Run the server

```bash
uvicorn app.api.routes:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Check it's alive:
```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

---

## 6. Request a demo video

```bash
curl -X POST http://127.0.0.1:8000/videos \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "defect-triaging-crewai",
    "project_id": "your-project-id",
    "custom_instructions": ""
  }'
```

The pipeline will pause at the **review_script** step for human approval. Once approved, both output files are written to `output/`.

---

## 7. Output files

| File | Description |
|------|-------------|
| `output/narrated_<agent_id>.mp4` | Full walkthrough with voice-over narration |
| `output/silent_<agent_id>.mp4` | Condensed cut with on-screen captions, no audio |

---

## Running with Docker (optional)

```bash
docker build -t demo-video-bot .
docker run --env-file .env -p 8000:8000 demo-video-bot
```

Or with Docker Compose:
```bash
docker compose up -d
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Missing required environment variable` | Check all fields are filled in `.env` |
| `playwright install` fails | Run as administrator / with `sudo` |
| `ffmpeg: command not found` | Add the `bin` folder of your FFmpeg extract to your user `PATH` (see Windows install steps above), then restart your terminal |
| Login fails during capture | Verify `HUB_EMAIL`, `HUB_PASSWORD`, and `AGENTICQEAHUB_BASE_URL` in `.env` |
| `google-genai` import error | Run `pip install -r requirements.txt` inside the active virtualenv |
