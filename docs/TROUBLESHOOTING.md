# Troubleshooting Guide

---

## Server / Startup

### `Missing required environment variable: GEMINI_API_KEY`
Copy `.env.example` to `.env` and fill in all required values. The server reads
from `.env` on startup — if a key is missing it refuses to start.

```bash
cp .env.example .env
# then open .env and fill in GEMINI_API_KEY, HUB_EMAIL, HUB_PASSWORD, etc.
```

### `ModuleNotFoundError: No module named 'edge_tts'` (or any other package)
You installed the package into the global Python instead of the project's virtual
environment. Always use the venv's pip:

```powershell
.\.venv\Scripts\pip install -r requirements.txt
```

### Server starts but immediately crashes
Check the terminal for the traceback. The most common causes:
- Missing `.env` values
- `truststore` failing on a non-Windows machine (safe to ignore — it falls back gracefully)
- Port 8000 already in use — kill the other process or run uvicorn on a different port (`--port 8001`)

---

## Gemini API

### `429 RESOURCE_EXHAUSTED` during script generation
The Gemini free tier has a daily request limit (~1,500/day). The retry logic waits
and retries automatically for per-minute limits, but a daily limit requires waiting
until midnight Pacific Time for the quota to reset.

To avoid this:
- Do not test the full pipeline repeatedly in the same day
- Ensure the API key is from a **different Google Cloud project** than any previous
  key (quota is shared within a project, not per-key)

### `certificate verify failed` (SSL error)
Cognizant's network uses an SSL-inspection proxy. The `truststore` package fixes
this automatically by using the Windows Certificate Store. If the error persists:
1. Confirm `truststore>=0.9` is installed in the venv
2. As a last resort, set `DISABLE_SSL_VERIFY=true` in `.env` (not recommended for production)

---

## Browser / Recording

### `Page.click: Timeout` on a button
The button is still disabled when the click is attempted. Possible causes:
- A form field was not filled correctly — check `RUN_INPUTS` in the agent config
- React's `onChange` did not fire — ensure `field_type` is `"fill"` (not `"click"`)
  for text inputs, so `press_sequentially` is used instead of `fill()`

### Screen recording is blank or very small
Run the server on a machine with an active display session (not a headless VM).
Recording requires a real screen — VMs without a GPU or display adapter may not work.

### Workspace content cut off on the right side
The 80% zoom is applied automatically in `navigate_to_agent_workspace`. If it's
still cut off, increase the zoom level in `hub_client.py`:
```python
page.evaluate("document.documentElement.style.zoom = '0.75'")  # try smaller values
```

### `Agent run did not complete within 600s`
The agent run timed out. Possible causes:
- A HITL prompt was not handled — check `HITL_RESPONSES` in the agent config,
  make sure `prompt_contains` matches text that actually appears on screen
- The agent itself crashed or stalled — check the platform for error messages
- The run legitimately takes longer — increase `_RUN_TIMEOUT` in `hub_client.py`

---

## Pipeline

### `No video file found in output/raw/ after capture`
Playwright failed to write the video file. This usually happens if the browser
context was not closed cleanly. Check the terminal for Playwright errors. The
context must be closed before the browser (`context.close()` then `browser.close()`).

### `ffprobe` errors during finalize
FFmpeg is not installed or not on PATH. Verify:
```bash
ffmpeg -version
ffprobe -version
```
Both must be available. See [INSTALL.md](INSTALL.md) for FFmpeg installation steps.

### Script review paused but browser closed
The pipeline checkpoint is held in memory (`MemorySaver`). If the server was
restarted while a job was paused at review, the job is lost. Re-run the pipeline
from scratch. (Swap `MemorySaver` for `SqliteSaver` for persistence across restarts.)

### `Scene X overlaps with scene X-1` validation error
Gemini returned scenes in the wrong order or with overlapping time ranges.
LangGraph retries `generate_script` automatically (up to 3 times). If it keeps
failing, add more specific custom instructions when submitting the job.

---

## Standalone Mode

### `demo_config.yaml not found`
The folder path is wrong or the file is missing. Check:
- The path uses the correct separator for your OS
- The file is named exactly `demo_config.yaml` (not `.yml`)
- See [STANDALONE_AGENT_MODE.md](STANDALONE_AGENT_MODE.md) for the full spec

### No video produced for a terminal agent
- Confirm FFmpeg is installed and `ffmpeg -version` works
- Confirm the agent process actually starts (run `command` manually in the folder)
- Check that `completion_signals` match phrases that actually appear in the agent's stdout

### Standalone web agent: browser opens but run appears to stall
- Increase `startup_wait_seconds` to give the server more time to start
- Confirm the server is actually listening on the configured `port`
- Check that `completion_signals` match text that actually appears in the page after the run

---

## Frontend

### Blank page in the browser
Make sure both servers are running:
- Backend: `cd backend && uvicorn app.api.routes:app --reload` (port 8000)
- Frontend: `cd frontend && npm run dev` (port 5173)

### `npm install` fails
Verify Node.js 18+ is installed: `node --version`. If behind a corporate proxy,
you may need to configure npm's proxy settings.

### "Pipeline Error" shown in the UI with no detail
Open the browser developer console (F12 → Console) for the full error message.
Also check the uvicorn terminal for the backend traceback.
