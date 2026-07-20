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

The form has a **Source** toggle at the top:

### Platform (Hub) mode
1. Select **Platform (Hub)** (default).
2. Enter the **Project Name** (e.g. `Dev test project`) and **Agent Name** (e.g. `Defect Triage (CrewAI)`) exactly as they appear in AgenticQEAHub, then click **Start Pipeline**.

### Standalone Folder mode
1. Select **Standalone Folder**.
2. Enter the **absolute path** to the local agent folder (e.g. `C:\Projects\my-agent`).
   - The folder must contain a `demo_config.yaml` file.
   - See [docs/STANDALONE_AGENT_MODE.md](STANDALONE_AGENT_MODE.md) for the full YAML spec.
3. Click **Start Pipeline**.

In both modes:
- The pipeline runs in the background. The page polls for status every 5 seconds automatically.
- When the narration script is ready, the **Scene Reviewer** appears — edit any caption or narration line, then click **Approve & Render** or **Submit Edits**.
- After rendering, the **Results** view shows both output file paths.

---

## 8. Output files

Output filenames are derived from the agent display name (spaces and special characters replaced with underscores):

| File | Description |
|------|-------------|
| `output/narrated_<agent_slug>.mp4` | Full walkthrough with voice-over narration |
| `output/silent_<agent_slug>.mp4` | Condensed cut with on-screen captions, no audio |

Example for "Defect Triage (CrewAI)": `narrated_defect_triage_crewai_.mp4`

---

## 9. Adding a new agent (HITL prompts)

When an agent pauses for user input during a run, the automation reads from
`agents/<agent_slug>.py` to know what to type. To add a new agent:

1. Copy `agents/defect_triage_crewai.py` and rename it (e.g. `agents/hcm_onboarding_langgraph.py`).
2. Watch a real run of that agent and note the exact prompt text shown at each HITL pause.
3. Update the `HITL_RESPONSES` list: set `prompt_contains` to a distinctive substring
   of each prompt and `response` to the answer the automation should type.
4. Register the new file in `agents/__init__.py` by adding a line to `_REGISTRY`:
   ```python
   "hcm_onboarding_langgraph": "agents.hcm_onboarding_langgraph",
   ```
5. That's it — the next pipeline run for that agent will pick up the config automatically.

---

## 10. Running with Docker (optional)

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
| `Could not find 'My Project'` | The project/agent name must match exactly what's shown in the platform UI (case-insensitive partial match) |
| `google-genai` import error | Run `pip install -r requirements.txt` inside the active virtualenv |
| Frontend shows blank page | Make sure `npm run dev` is running and the backend is up on `:8000` |
| `npm install` fails | Verify Node.js 18+ is installed: `node --version` |
| Agent run times out during HITL | Check `agents/<agent>.py` — add or fix the `prompt_contains` entry for the prompt that isn't being handled |
| Standalone: `demo_config.yaml not found` | The folder path is wrong or the file is missing — create it using the spec in `docs/STANDALONE_AGENT_MODE.md` |
| Standalone (terminal): no video produced | Confirm FFmpeg is installed and `ffmpeg -version` works; check the agent's `demo_config.yaml` `completion_signals` match actual stdout output |
| Standalone (web): browser opens but run stalls | Increase `startup_wait_seconds` in `demo_config.yaml` or check that the local server is actually listening on the configured `port` |
