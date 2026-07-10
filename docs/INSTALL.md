# Installation & Setup Guide

## Prerequisites

Make sure the following are installed on your machine before proceeding.

| Requirement | Minimum version | Install |
|-------------|----------------|---------|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| FFmpeg | any recent | See below |
| Git | any | [git-scm.com](https://git-scm.com/) |

### Installing FFmpeg

FFmpeg is a system dependency — it is **not** a pip package.

**Windows (manual — no admin or package manager required)**

1. Go to **[https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)** (the official Windows builds linked from ffmpeg.org).
2. Under **"release builds"**, download `ffmpeg-release-essentials.zip`.
3. Extract the zip — you'll get a folder like `ffmpeg-8.x-essentials_build\`.
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
python -m playwright install chromium
```

This downloads the Chromium browser binary used for login and screen recording.

> **Windows note:** use `python -m playwright install chromium` rather than `playwright install chromium` — the `playwright` CLI may not be on the PATH depending on how Python was installed.

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

# Set to true to skip the human review step (useful for re-renders)
SKIP_REVIEW=false
```

> **Never commit `.env`.** It is already listed in `.gitignore`.
> Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

---

## 5. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

## 6. Run the app (development)

Open **two terminals** in the project root:

**Terminal 1 — backend**
```bash
uvicorn app.api.routes:app --reload
```
API available at `http://127.0.0.1:8000`. Verify:
```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

**Terminal 2 — frontend**
```bash
cd frontend
npm run dev
```
React app available at `http://localhost:5173`. Open this URL in your browser.

The Vite dev server proxies all `/videos` and `/health` requests to the backend automatically — no CORS issues.

---

## 7. Using the UI

1. Enter the **Agent ID** and **Project ID** in the form and click **Start Pipeline**.
2. The pipeline runs in the background (~5–10 min). The page polls for status every 5 seconds automatically.
3. When the narration script is ready, the **Scene Reviewer** appears — edit any on-screen caption or narration line, then click **Approve & Render** or **Submit Edits**.
4. After rendering, the **Results** view shows both output file paths.

---

## 8. Output files

| File | Description |
|------|-------------|
| `output/narrated_<agent_id>.mp4` | Full walkthrough with voice-over narration |
| `output/silent_<agent_id>.mp4` | Condensed cut with on-screen captions, no audio |

---

## 9. Running with Docker (optional)

The Dockerfile uses a multi-stage build — it builds the React frontend first,
then packages everything into a single Python image. No Node.js needed on the host.

```bash
docker build -t demo-video-bot .
docker run --env-file .env -p 8000:8000 demo-video-bot
```

Or with Docker Compose:
```bash
docker compose up -d
```

The app (backend + frontend) is served at `http://localhost:8000`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Missing required environment variable` | Check all fields are filled in `.env` |
| `playwright install` fails | Run as administrator / with `sudo` |
| `ffmpeg: command not found` | Add the `bin` folder of your FFmpeg extract to your user `PATH` (see Windows install steps above), then restart your terminal |
| Login fails during capture | Verify `HUB_EMAIL`, `HUB_PASSWORD`, and `AGENTICQEAHUB_BASE_URL` in `.env` |
| `google-genai` import error | Run `pip install -r requirements.txt` inside the active virtualenv |
| Frontend shows blank page | Make sure `npm run dev` is running and the backend is up on `:8000` |
| `npm install` fails | Verify Node.js 18+ is installed: `node --version` |
