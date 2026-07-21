"""Standalone agent execution and screen recording.

Handles running a local agent folder (not on the AgenticQEAHub platform) and
producing a screen-recorded video for the demo video pipeline.

The agent folder must contain a demo_config.yaml file.
See docs/STANDALONE_AGENT_MODE.md for the full spec.

Two execution paths:
  terminal — FFmpeg records the desktop; agent runs as a subprocess; HITL
             responses are written to the process stdin.
  web      — agent starts a local server; Playwright opens a browser and
             records it (same approach as the hub flow).
"""

import os
import re
import subprocess
import threading
import time
from pathlib import Path

import structlog
import yaml

log = structlog.get_logger()

_DEFAULT_TIMEOUT  = 300   # seconds — overridden by demo_config timeout_seconds
_POLL_INTERVAL    = 2     # seconds — how often to poll for completion / HITL
_FFMPEG_STOP_WAIT = 15    # seconds — graceful FFmpeg shutdown before kill


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_demo_config(agent_folder: str) -> dict:
    """Read and validate demo_config.yaml from the agent folder.

    Raises FileNotFoundError if the file is missing.
    Raises ValueError if required fields are absent.
    Environment variable references (${VAR}) in string values are expanded.
    """
    folder = Path(agent_folder)
    config_path = folder / "demo_config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"demo_config.yaml not found in '{agent_folder}'. "
            "Create this file to configure the standalone agent run. "
            "See docs/STANDALONE_AGENT_MODE.md for the full spec."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    cfg = _expand_env_vars(cfg)

    if not cfg.get("agent_name"):
        raise ValueError("demo_config.yaml must have a non-empty 'agent_name' field.")
    if not cfg.get("run", {}).get("command"):
        raise ValueError("demo_config.yaml must have a non-empty 'run.command' field.")

    return cfg


def _expand_env_vars(obj):
    """Recursively expand ${VAR} references using the host environment.

    Unknown variables are left as-is (${UNKNOWN_VAR} stays unchanged)
    so the agent gets a clear hint rather than a silent empty string.
    """
    if isinstance(obj, str):
        return re.sub(
            r"\$\{([^}]+)\}",
            lambda m: os.environ.get(m.group(1), m.group(0)),
            obj,
        )
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Main entry point (called from capture_run node)
# ---------------------------------------------------------------------------

def run_and_record(
    agent_folder: str,
    demo_config: dict,
    output_dir: str,
) -> tuple[str, list[dict]]:
    """Launch the agent, record the screen, return (video_path, transcript).

    Branches on demo_config["ui"]["type"]:
      "terminal" (default) — FFmpeg records the desktop while the agent runs.
      "web"                — Playwright opens and records the local web UI.
    """
    ui_type = demo_config.get("ui", {}).get("type", "terminal")
    log.info("standalone.run_and_record", ui_type=ui_type, folder=agent_folder)

    if ui_type == "web":
        return _run_web_agent(agent_folder, demo_config, output_dir)
    return _run_terminal_agent(agent_folder, demo_config, output_dir)


# ---------------------------------------------------------------------------
# Terminal agent path
# ---------------------------------------------------------------------------

def _run_terminal_agent(
    agent_folder: str,
    demo_config: dict,
    output_dir: str,
) -> tuple[str, list[dict]]:
    """Record the desktop with FFmpeg while the agent runs in a subprocess.

    HITL responses (response_type "stdin") are written to the process stdin
    when the matching prompt_contains text appears in stdout.
    """
    folder      = Path(agent_folder)
    run_cfg     = demo_config.get("run", {})
    command     = run_cfg["command"]
    working_dir = folder / run_cfg.get("working_dir", ".")
    extra_env   = {**os.environ, **{k: str(v) for k, v in run_cfg.get("env", {}).items()}}

    timeout           = int(demo_config.get("timeout_seconds", _DEFAULT_TIMEOUT))
    hitl_responses    = demo_config.get("hitl_responses", [])
    completion_signals = [s.lower() for s in demo_config.get("completion_signals", [])]

    # Output video — timestamp avoids collisions between concurrent jobs.
    out_path = Path(output_dir) / f"standalone_{int(time.time())}.mp4"

    log.info("standalone.terminal.start", command=command, out=str(out_path))

    ffmpeg_proc = _start_ffmpeg_recording(str(out_path))

    proc = subprocess.Popen(
        command,
        shell=True,
        cwd=str(working_dir),
        env=extra_env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Background thread accumulates stdout so the main loop can poll it.
    stdout_lines: list[str] = []
    lines_lock   = threading.Lock()

    def _reader():
        for line in proc.stdout:
            with lines_lock:
                stdout_lines.append(line.rstrip())

    threading.Thread(target=_reader, daemon=True).start()

    responded = set()
    deadline  = time.time() + timeout
    completed = False

    try:
        while time.time() < deadline:
            with lines_lock:
                snapshot = list(stdout_lines)

            full_text = "\n".join(snapshot).lower()

            if completion_signals and any(s in full_text for s in completion_signals):
                log.info("standalone.terminal.completion_detected")
                completed = True
                break

            if proc.poll() is not None:
                log.info("standalone.terminal.process_exited", returncode=proc.returncode)
                completed = True
                break

            for i, hitl in enumerate(hitl_responses):
                if i in responded:
                    continue
                trigger = hitl.get("prompt_contains", "").lower()
                if not trigger or trigger not in full_text:
                    continue
                response = hitl.get("response", "")
                try:
                    proc.stdin.write(response + "\n")
                    proc.stdin.flush()
                    responded.add(i)
                    log.info("standalone.terminal.hitl_responded", trigger=trigger, response=response)
                except Exception:
                    pass

            time.sleep(_POLL_INTERVAL)

        if not completed:
            log.warning("standalone.terminal.timeout", timeout=timeout)
    finally:
        _terminate_process(proc)
        _stop_ffmpeg(ffmpeg_proc)

    with lines_lock:
        final_lines = list(stdout_lines)

    transcript = [
        {"type": "output", "content": line}
        for line in final_lines
        if line.strip()
    ]
    return str(out_path), transcript


# ---------------------------------------------------------------------------
# Web UI agent path
# ---------------------------------------------------------------------------

def _run_web_agent(
    agent_folder: str,
    demo_config: dict,
    output_dir: str,
) -> tuple[str, list[dict]]:
    """Start the agent's local web server and record it with Playwright.

    Uses the same fill/HITL/completion helpers as the hub flow so behaviour
    is consistent — only the browser URL differs.
    """
    from playwright.sync_api import sync_playwright

    from app.clients.hub_client import _fill_run_inputs, _handle_hitl, _collect_events

    folder      = Path(agent_folder)
    run_cfg     = demo_config.get("run", {})
    command     = run_cfg["command"]
    working_dir = folder / run_cfg.get("working_dir", ".")
    extra_env   = {**os.environ, **{k: str(v) for k, v in run_cfg.get("env", {}).items()}}

    ui_cfg        = demo_config.get("ui", {})
    port          = int(ui_cfg.get("port", 7860))
    startup_wait  = int(ui_cfg.get("startup_wait_seconds", 10))

    run_inputs        = demo_config.get("run_inputs", [])
    hitl_responses    = demo_config.get("hitl_responses", [])
    completion_signals = demo_config.get("completion_signals", [])
    timeout           = int(demo_config.get("timeout_seconds", _DEFAULT_TIMEOUT))

    raw_dir = Path(output_dir)
    log.info("standalone.web.start", port=port, command=command)

    server_proc = subprocess.Popen(
        command,
        shell=True,
        cwd=str(working_dir),
        env=extra_env,
    )

    log.info("standalone.web.waiting_for_server", seconds=startup_wait)
    time.sleep(startup_wait)

    events: list[dict] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--start-maximized"])
            context = browser.new_context(
                record_video_dir=str(raw_dir),
                record_video_size={"width": 1920, "height": 1080},
                no_viewport=True,
                ignore_https_errors=True,
            )
            page = context.new_page()

            page.goto(f"http://localhost:{port}", timeout=30_000)
            page.wait_for_load_state("networkidle", timeout=30_000)
            page.evaluate("document.documentElement.style.zoom = '0.8'")

            if run_inputs:
                _fill_run_inputs(page, run_inputs)

            _wait_for_web_completion(page, hitl_responses, completion_signals, timeout)

            events = _collect_events(page)

            context.close()
            browser.close()
    finally:
        _terminate_process(server_proc)

    video_path = _latest_video_in(raw_dir)
    return video_path, events


def _wait_for_web_completion(
    page,
    hitl_responses: list[dict],
    completion_signals: list[str],
    timeout: int,
) -> None:
    """Poll the web page until the agent run completes, handling HITL along the way.

    Mirrors hub_client._wait_for_completion but uses a configurable timeout
    and completion signals from demo_config instead of hardcoded values.
    """
    from app.clients.hub_client import _handle_hitl

    done_phrases = [s.lower() for s in completion_signals] or ["completed"]

    deadline       = time.time() + timeout
    start_deadline = time.time() + 30
    run_started    = False
    responded      = set()

    _START_SIGNALS = ["running", "processing", "generating", "loading"]

    while time.time() < deadline:
        try:
            page_text = page.evaluate("() => document.body.innerText.toLowerCase()")
        except Exception:
            time.sleep(_POLL_INTERVAL)
            continue

        if not run_started:
            if any(s in page_text for s in _START_SIGNALS) or time.time() > start_deadline:
                run_started = True

        if run_started and any(phrase in page_text for phrase in done_phrases):
            log.info("standalone.web.completion_detected")
            return

        if hitl_responses:
            _handle_hitl(page, hitl_responses, responded, page_text)

        time.sleep(_POLL_INTERVAL)

    raise RuntimeError(
        f"Standalone web agent did not complete within {timeout}s. "
        "Increase timeout_seconds in demo_config.yaml or check the agent logs."
    )


# ---------------------------------------------------------------------------
# FFmpeg helpers (terminal path only)
# ---------------------------------------------------------------------------

def _start_ffmpeg_recording(output_path: str) -> subprocess.Popen:
    """Start FFmpeg desktop capture (Windows gdigrab) in the background."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "gdigrab",
        "-framerate", "30",
        "-i", "desktop",
        "-vcodec", "libx264",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _stop_ffmpeg(proc: subprocess.Popen) -> None:
    """Send 'q' to FFmpeg's stdin to trigger a graceful, non-corrupt shutdown."""
    try:
        proc.stdin.write(b"q\n")
        proc.stdin.flush()
        proc.wait(timeout=_FFMPEG_STOP_WAIT)
    except Exception:
        proc.kill()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _terminate_process(proc: subprocess.Popen) -> None:
    """Terminate a subprocess, escalating to kill if it doesn't exit cleanly."""
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _latest_video_in(directory: Path) -> str:
    """Return the path of the most recently written video file in directory."""
    videos = sorted(
        list(directory.glob("*.webm")) + list(directory.glob("*.mp4")),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not videos:
        raise RuntimeError(
            f"No video file found in {directory} after recording. "
            "Check that FFmpeg ran successfully and the output path is writable."
        )
    return str(videos[0])
