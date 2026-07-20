# Agent Configuration Guide

This guide explains how to configure DemoVideoBot to run a specific agent —
both platform agents (on AgenticQEAHub) and standalone agents (local folders).

---

## Platform Agents (Hub mode)

Platform agents run on the AgenticQEAHub platform. DemoVideoBot logs in, navigates
to the agent's workspace, fills the run form, clicks through any mid-run prompts
(HITL), and records everything.

Each platform agent needs its own config file in the `agents/` directory.

### Step 1 — Create the config file

Copy an existing file as a starting point:

```bash
cp agents/defect_triage_crewai.py agents/my_new_agent.py
```

### Step 2 — Fill in the config

```python
# agents/my_new_agent.py

AGENT_NAME = "My New Agent"
AGENT_SLUG = "my-new-agent"

# ── RUN_INPUTS ────────────────────────────────────────────────────────────────
# Actions taken on the workspace form before clicking the submit button.
# Executed in order. Supported field_type values:
#   "click"  — click an element (e.g. a tab button to switch the form view)
#   "fill"   — type into an input or textarea (fires React's onChange per key)
#   "select" — choose from a <select> dropdown by value
#   "submit" — the submit button; handled by _start_run(), not _fill_run_inputs()

RUN_INPUTS: list[dict] = [
    # Example: click a tab first
    {"label": "Select Neo4j tab", "field_type": "click",
     "selector": "button:has-text('Neo4j Lookup')"},

    # Example: fill a text field
    {"label": "Defect ID", "field_type": "fill",
     "selector": "input", "nth": 0, "value": "80"},

    # Example: the submit button
    {"label": "Submit", "field_type": "submit", "value": "Triage Defect"},
]

# ── HITL_RESPONSES ────────────────────────────────────────────────────────────
# Mid-run prompts the agent pauses on, waiting for a human to respond.
# DemoVideoBot detects the prompt text and automatically clicks the response.
#
# prompt_contains — a distinctive substring of the prompt text (case-insensitive)
# response        — the text of the element to click (button label or list item text)
# response_type   — "button" clicks <button> elements (default)
#                   "text"   clicks any element whose text contains `response`
#                            (use for assignee lists, dropdowns, etc.)

HITL_RESPONSES: list[dict] = [
    {
        "prompt_contains": "continue with defect analyzer",
        "response": "YES",
        "response_type": "button",
    },
    {
        "prompt_contains": "skip assignment",
        "response": "Arul Amuthan, Ahill Savio (Cognizant)",
        "response_type": "text",
    },
]

# ── COMPLETION_TEXTS ──────────────────────────────────────────────────────────
# Phrases that appear in the page text when the agent run is fully finished.
# DemoVideoBot polls the page and stops recording when any of these is found.
# Use specific, distinctive phrases from the agent's final output screen.
# Falls back to the generic word "completed" if this list is left empty.

COMPLETION_TEXTS: list[str] = [
    "flow ended",
    "triage summary",
    "successfully assigned defect",
    "resolution published to ado",
]
```

### Step 3 — Register the agent

Open `agents/__init__.py` and add a line to `_REGISTRY`:

```python
_REGISTRY: dict[str, str] = {
    "defect_triaging":        "agents.defect_triaging",
    "defect_triage_crewai":   "agents.defect_triage_crewai",

    # Add your new agent here:
    "my_new_agent":           "agents.my_new_agent",
}
```

The key is the **normalised slug** of the agent's display name:
lowercase, non-alphanumeric characters replaced with `_`, leading/trailing `_` stripped.

Examples:
- `"Defect Triage (CrewAI)"` → `"defect_triage__crewai_"`
- `"HCM Onboarding (LangGraph)"` → `"hcm_onboarding__langgraph_"`
- `"My New Agent"` → `"my_new_agent"`

If you are unsure of the slug, run:
```python
import re
name = "My New Agent"
print(re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_"))
# → my_new_agent
```

### Step 4 — Verify selectors

Before running the full pipeline, inspect the actual platform UI:

1. Open the agent's workspace page in a browser.
2. Right-click each form field → Inspect to confirm the CSS selector.
3. Note the exact text of each HITL prompt and the buttons/options shown.
4. Note the exact text shown when the run finishes.
5. Update `RUN_INPUTS`, `HITL_RESPONSES`, and `COMPLETION_TEXTS` accordingly.

> **Tip:** The `scripts/` folder contains diagnostic scripts you can run against
> the live platform to map selectors interactively.

---

## Standalone Agents (Standalone mode)

Standalone agents run locally on your machine — Python scripts, Gradio/Streamlit
apps, CLI tools, or anything else. No platform login is needed.

The only requirement: the agent folder must contain a `demo_config.yaml` file.

### `demo_config.yaml` full spec

```yaml
# ── Identity ──────────────────────────────────────────────────────────────────
agent_name: "My Local Agent"
agent_description: >
  One or two sentences describing what the agent does.
  Used by Gemini when writing the narration script.

# ── How to run ────────────────────────────────────────────────────────────────
run:
  command: "python main.py"       # Shell command, run from inside the folder
  working_dir: "."                # Relative to the agent folder
  env:                            # Extra env vars for the subprocess
    MY_API_KEY: "${MY_API_KEY}"   # ${VAR} is expanded from the host environment

# ── UI type ───────────────────────────────────────────────────────────────────
ui:
  type: terminal                  # "terminal" or "web"

  # Only needed when type is "web":
  port: 7860                      # Port the local web server listens on
  startup_wait_seconds: 10        # How long to wait before opening the browser

# ── Pre-run form inputs (web UI agents only) ──────────────────────────────────
# Same structure as RUN_INPUTS in platform agents.
# Omit if the agent needs no form input before starting.
run_inputs:
  - label: "Query"
    field_type: fill
    selector: "textarea"
    nth: 0
    value: "Analyse this dataset"

# ── HITL responses ────────────────────────────────────────────────────────────
# For terminal agents: response_type must be "stdin" — writes to process stdin.
# For web agents:      "button" or "text" — same as platform agents.
hitl_responses:
  - prompt_contains: "continue?"
    response: "yes"
    response_type: stdin

  - prompt_contains: "select an option"
    response: "Option A"
    response_type: stdin

# ── Completion signals ────────────────────────────────────────────────────────
# Terminal: phrases to watch for in stdout.
# Web:      phrases to watch for in the browser page text.
completion_signals:
  - "run complete"
  - "finished successfully"

# ── Timeout ───────────────────────────────────────────────────────────────────
timeout_seconds: 300              # Max run time (default 300)
```

### Environment variable expansion

String values in `demo_config.yaml` can reference environment variables:

```yaml
run:
  env:
    API_KEY: "${MY_SECRET_KEY}"   # expanded from the host environment
```

Unknown variables are left as-is (`${UNKNOWN}` stays `${UNKNOWN}`) so you get
a clear hint rather than a silent empty string.

### Terminal agent example

```yaml
agent_name: "Defect Classifier CLI"
agent_description: >
  A command-line agent that classifies software defects by severity
  using a fine-tuned model and outputs a structured report.

run:
  command: "python classify.py --defect-id 80 --output report.json"
  working_dir: "."

ui:
  type: terminal

completion_signals:
  - "classification complete"
  - "report written"

timeout_seconds: 120
```

### Web UI agent example (Gradio)

```yaml
agent_name: "Document Summariser"
agent_description: >
  A Gradio web app that summarises long documents using an LLM.

run:
  command: "python app.py"
  working_dir: "."
  env:
    OPENAI_API_KEY: "${OPENAI_API_KEY}"

ui:
  type: web
  port: 7860
  startup_wait_seconds: 15

run_inputs:
  - label: "Upload document text"
    field_type: fill
    selector: "textarea"
    nth: 0
    value: "Paste your document here..."

completion_signals:
  - "summary ready"
  - "generation complete"

timeout_seconds: 180
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Run completes but recording stops early | Add more phrases to `COMPLETION_TEXTS` / `completion_signals` |
| HITL prompt not clicked | Check `prompt_contains` is a distinctive substring of the actual prompt text |
| Submit button stays disabled | The form value may not be triggering React's `onChange` — verify the `field_type` is `"fill"` not `"click"` |
| Agent times out | Increase `_RUN_TIMEOUT` in `hub_client.py` (platform) or `timeout_seconds` in `demo_config.yaml` (standalone) |
| Standalone: no video produced | Check FFmpeg is on PATH; check `completion_signals` match actual stdout output |
| Standalone web: page opens but stalls | Increase `startup_wait_seconds`; confirm the server is actually listening on the configured port |
