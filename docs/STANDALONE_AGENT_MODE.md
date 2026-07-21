# Standalone Agent Mode — Design & Implementation Guide

This document covers how to extend DemoVideoBot to produce demo videos for a
**local / standalone agent** — one that runs as a process on your machine rather
than on the AgenticQEAHub platform.

Everything from `generate_script` onward (script writing, TTS, assembly, finalize)
is identical to the platform flow.  Only `select_agent` and `capture_run` change.

---

## 1. What "standalone" means

The user provides a **folder** that contains a runnable agent project.  The agent
may be:

| UI type    | How it runs                                      | Example                        |
|------------|--------------------------------------------------|--------------------------------|
| `terminal` | CLI process — output goes to stdout/stderr       | Python script, LangChain CLI   |
| `web`      | Starts a local web server; user opens a browser  | Gradio, Streamlit, FastAPI UI  |

The pipeline needs to:
1. Read the agent's metadata (name, description) from the folder.
2. Launch the agent process.
3. Record the screen while it runs.
4. Handle any mid-run prompts (HITL).
5. Detect when the run is done.
6. Hand the raw video to the existing script/audio/assembly pipeline.

---

## 2. Required folder structure

The agent folder must contain a **`demo_config.yaml`** file.  This is the only
new convention imposed on the standalone agent.

```
my-agent/
├── demo_config.yaml        ← required by DemoVideoBot
├── main.py                 ← (or whatever the entry point is)
├── requirements.txt
└── ...
```

### `demo_config.yaml` spec

```yaml
# --- Identity (used in the narration script) ---
agent_name: "My Awesome Agent"
agent_description: >
  One or two sentences describing what the agent does and what the demo shows.

# --- How to run the agent ---
run:
  command: "python main.py"       # shell command executed from inside the folder
  working_dir: "."                # relative to the agent folder; usually "."
  env:                            # optional extra env vars for the subprocess
    MY_API_KEY: "${MY_API_KEY}"   # ${VAR} is expanded from the host environment

# --- UI type ---
ui:
  type: terminal                  # "terminal" or "web"
  # Only needed when type is "web":
  port: 7860                      # local port the agent's web server listens on
  startup_wait_seconds: 10        # how long to wait before opening the browser

# --- Run inputs (pre-run form fill, web UI only) ---
# Same structure as RUN_INPUTS in the platform backend/agents/ config.
# Omit entirely if the agent needs no form input before running.
run_inputs:
  - label: "Query"
    field_type: fill
    selector: "textarea"
    nth: 0
    value: "Analyze this dataset"

# --- HITL responses (mid-run prompts) ---
# Same structure as HITL_RESPONSES in the platform backend/agents/ config.
# Use response_type "stdin" for terminal agents (types into the process stdin).
# Use response_type "button" or "text" for web UI agents (clicks in the browser).
hitl_responses:
  - prompt_contains: "continue?"
    response: "yes"
    response_type: stdin          # "stdin" | "button" | "text"
  - prompt_contains: "select an option"
    response: "Option A"
    response_type: stdin

# --- Completion detection ---
# For terminal: phrases to watch for in the process stdout.
# For web:      phrases to watch for in the browser page text (same as platform flow).
completion_signals:
  - "run complete"
  - "finished successfully"

# --- Timeouts ---
timeout_seconds: 300              # max run time before treating as failure (default 300)
```

---

## 3. Pipeline changes

### 3.1  State (`backend/app/agent/state.py`)

Add two new optional fields:

```python
source_type: str        # "hub" (default) | "standalone"
agent_folder: str       # absolute path to the folder (standalone only)
```

The existing `agent_name`, `project_name`, `agent_spec` fields are still used;
for standalone runs `agent_name` and `agent_spec` are populated from
`demo_config.yaml` instead of the platform.

### 3.2  `select_agent` node

Branch on `source_type`:

- **`"hub"`** — current behaviour unchanged.
- **`"standalone"`** — read `demo_config.yaml` from `agent_folder`, populate
  `agent_name` and `agent_spec` from it.  No browser, no network call.

```python
# pseudo-code
if state["source_type"] == "standalone":
    cfg = load_demo_config(state["agent_folder"])
    return {
        "agent_display_name": cfg["agent_name"],
        "agent_spec": cfg["agent_description"],
    }
else:
    # existing hub_client.get_agent_spec(...) call
```

### 3.3  `capture_run` node

Branch on `source_type`:

- **`"hub"`** — current behaviour unchanged.
- **`"standalone"`** — call the new `standalone_client.run_and_record(...)`.

---

## 4. New module: `backend/app/clients/standalone_client.py`

This module handles everything specific to the standalone flow.

### 4.1  Screen recording strategy

Use **FFmpeg's `gdigrab`** (Windows screen capture) to record the desktop while
the agent runs.  This works for both terminal and web UI agents without needing
Playwright's recording context.

```
ffmpeg -f gdigrab -framerate 30 -i desktop -vcodec libx264 -pix_fmt yuv420p output.mp4
```

Start FFmpeg as a background subprocess, let the agent run, then stop FFmpeg
when done (send `q\n` to its stdin or `SIGTERM`).

### 4.2  Terminal agent flow

```
1. Start FFmpeg recording (background subprocess)
2. Launch agent command (subprocess, capture stdout/stderr for transcript)
3. Poll stdout line by line:
     a. Check completion_signals → if found, stop agent + FFmpeg
     b. Check hitl_responses → if prompt found, write response to agent stdin
4. On timeout: terminate agent + FFmpeg, raise RuntimeError
5. Return raw video path + collected stdout as transcript
```

HITL for terminal: write `response + "\n"` to the agent process's `stdin`.

### 4.3  Web UI agent flow

```
1. Start agent command (background subprocess, not captured — it runs a server)
2. Wait startup_wait_seconds for the server to come up
3. Start Playwright browser (headless=False, record_video_dir=raw_dir)
4. Navigate to http://localhost:{port}
5. Fill run_inputs via _fill_run_inputs() (same helper as hub flow)
6. Start FFmpeg recording OR use Playwright's record_video (choose one approach)
7. Poll page text for completion_signals and hitl_responses
     — uses the same _wait_for_completion / _handle_hitl helpers as hub flow
8. Close browser, stop agent subprocess
9. Return raw video path
```

> **Recommended**: for web UI agents, use **Playwright's built-in `record_video_dir`**
> (same as the hub flow) rather than FFmpeg.  This keeps the recording code
> consistent and avoids dealing with desktop window ordering.  Use FFmpeg only
> for pure terminal agents.

### 4.4  Transcript for standalone

For terminal agents the transcript is the stdout/stderr text, split into lines
and wrapped as `[{"type": "output", "content": line}]` — the same shape that
`_collect_events` returns for the hub flow.  `generate_script` already handles
this format.

---

## 5. UI changes (`frontend/src/`)

### 5.1  Source type toggle

Add a **"Source"** radio/toggle to `PipelineForm`:

```
○ Platform (Hub)     ● Standalone agent folder
```

### 5.2  Form fields per source type

| Source type   | Fields shown                                      |
|---------------|---------------------------------------------------|
| Hub           | Project Name, Agent Name (current behaviour)      |
| Standalone    | Agent Folder Path (text input for the local path) |

Both show the existing Custom Instructions field below.

### 5.3  API change (`backend/app/api/routes.py`)

Accept two new body fields:

```json
{
  "source_type": "standalone",
  "agent_folder": "C:/Users/.../my-agent"
}
```

When `source_type` is `"hub"` (or omitted), behaviour is identical to today.

---

## 6. New files to create

| File | Purpose |
|------|---------|
| `backend/app/clients/standalone_client.py` | FFmpeg recording, subprocess launch, HITL via stdin |
| `backend/app/agent/nodes/select_agent_standalone.py` | OR add a branch inside the existing `select_agent.py` |

Preference: add branches **inside the existing nodes** (`select_agent.py`,
`capture_run.py`) rather than creating separate node files — the graph wiring
stays the same and the branch is a few lines.

---

## 7. Dependencies

No new pip packages are needed if you use the Playwright recording path for
web UI agents.  For terminal agents using FFmpeg recording, FFmpeg must already
be installed (it is a listed system dependency in `docs/INSTALL.md`).

If you want Python-side FFmpeg control, `ffmpeg-python` is a thin wrapper:

```
ffmpeg-python>=0.2
```

But calling `subprocess.Popen(["ffmpeg", ...])` directly is simpler and avoids
an extra dependency.

---

## 8. Implementation order

Work through this in order — each step is independently testable:

1. **`demo_config.yaml` loader** — a function that reads and validates the file.
   Write a unit test that loads a sample config from a fixture folder.

2. **`select_agent` branch** — populate state from the config file.
   Confirm the node returns correct `agent_display_name` and `agent_spec`.

3. **FFmpeg recording** — start/stop FFmpeg around a `time.sleep(5)` stub.
   Confirm a valid `.mp4` is written.

4. **Terminal agent subprocess + HITL** — run a trivial Python script that
   prints a prompt and waits for stdin; confirm the client responds and detects
   completion.

5. **Full terminal standalone run** — wire steps 3 + 4 into `capture_run`.

6. **Web UI path** (optional, do after terminal path is solid) — Playwright
   records a locally running Gradio/Streamlit app.

7. **UI toggle + API field** — frontend source selector and backend route update.

8. **End-to-end test** — run the full pipeline against a real local agent folder.

---

## 9. Key constraints (unchanged from CLAUDE.md)

- `demo_config.yaml` may reference env vars with `${VAR}` syntax but must never
  contain real secret values.
- All selectors for web UI agents go in `standalone_client.py` (same principle
  as hub selectors living in `hub_client.py`).
- The `backend/agents/` directory is for **platform agents only** — standalone agent
  config lives inside the agent's own folder (`demo_config.yaml`).
