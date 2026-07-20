"""Unit tests for the standalone agent config loader.

These tests only cover pure-Python logic (YAML loading, env-var expansion,
validation).  The actual recording functions (FFmpeg, Playwright) are not
tested here because they require a live screen, FFmpeg binary, and a running
agent process — those are tested manually during integration testing.
"""

import os
import textwrap
from pathlib import Path

import pytest

from app.clients.standalone_client import load_demo_config, _expand_env_vars


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "demo_agent"


# ---------------------------------------------------------------------------
# load_demo_config — happy path
# ---------------------------------------------------------------------------

def test_load_demo_config_valid():
    cfg = load_demo_config(str(FIXTURE_DIR))
    assert cfg["agent_name"] == "Sample Demo Agent"
    assert cfg["run"]["command"] == "python main.py"
    assert cfg["ui"]["type"] == "terminal"
    assert cfg["timeout_seconds"] == 60


def test_load_demo_config_returns_hitl_list():
    cfg = load_demo_config(str(FIXTURE_DIR))
    assert isinstance(cfg["hitl_responses"], list)
    assert cfg["hitl_responses"][0]["response"] == "yes"


def test_load_demo_config_returns_completion_signals():
    cfg = load_demo_config(str(FIXTURE_DIR))
    assert "done" in cfg["completion_signals"]
    assert "finished" in cfg["completion_signals"]


# ---------------------------------------------------------------------------
# load_demo_config — error cases
# ---------------------------------------------------------------------------

def test_load_demo_config_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="demo_config.yaml not found"):
        load_demo_config(str(tmp_path))


def test_load_demo_config_missing_agent_name(tmp_path):
    (tmp_path / "demo_config.yaml").write_text(
        textwrap.dedent("""\
        run:
          command: "python main.py"
        """)
    )
    with pytest.raises(ValueError, match="agent_name"):
        load_demo_config(str(tmp_path))


def test_load_demo_config_missing_command(tmp_path):
    (tmp_path / "demo_config.yaml").write_text(
        textwrap.dedent("""\
        agent_name: "My Agent"
        run:
          working_dir: "."
        """)
    )
    with pytest.raises(ValueError, match="run.command"):
        load_demo_config(str(tmp_path))


def test_load_demo_config_empty_file(tmp_path):
    (tmp_path / "demo_config.yaml").write_text("")
    with pytest.raises(ValueError):
        load_demo_config(str(tmp_path))


# ---------------------------------------------------------------------------
# _expand_env_vars
# ---------------------------------------------------------------------------

def test_expand_env_vars_string(monkeypatch):
    monkeypatch.setenv("MY_KEY", "secret123")
    result = _expand_env_vars("token=${MY_KEY}")
    assert result == "token=secret123"


def test_expand_env_vars_unknown_var_left_as_is():
    result = _expand_env_vars("${TOTALLY_UNKNOWN_VAR_XYZ}")
    assert result == "${TOTALLY_UNKNOWN_VAR_XYZ}"


def test_expand_env_vars_dict(monkeypatch):
    monkeypatch.setenv("API_HOST", "localhost")
    result = _expand_env_vars({"url": "http://${API_HOST}:8080"})
    assert result["url"] == "http://localhost:8080"


def test_expand_env_vars_nested(monkeypatch):
    monkeypatch.setenv("PORT", "9000")
    obj = {"run": {"env": {"ADDR": "0.0.0.0:${PORT}"}}}
    result = _expand_env_vars(obj)
    assert result["run"]["env"]["ADDR"] == "0.0.0.0:9000"


def test_expand_env_vars_list(monkeypatch):
    monkeypatch.setenv("ITEM", "hello")
    result = _expand_env_vars(["${ITEM}", "world"])
    assert result == ["hello", "world"]


def test_expand_env_vars_non_string_passthrough():
    assert _expand_env_vars(42)    == 42
    assert _expand_env_vars(True)  is True
    assert _expand_env_vars(None)  is None


# ---------------------------------------------------------------------------
# load_demo_config — env var expansion integration
# ---------------------------------------------------------------------------

def test_load_demo_config_expands_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_CMD", "python run.py")
    (tmp_path / "demo_config.yaml").write_text(
        textwrap.dedent("""\
        agent_name: "Env Var Agent"
        run:
          command: "${DEMO_CMD}"
        """)
    )
    cfg = load_demo_config(str(tmp_path))
    assert cfg["run"]["command"] == "python run.py"


# ---------------------------------------------------------------------------
# Web UI config fields
# ---------------------------------------------------------------------------

def test_load_demo_config_web_ui_fields(tmp_path):
    (tmp_path / "demo_config.yaml").write_text(
        textwrap.dedent("""\
        agent_name: "Web Agent"
        agent_description: "Runs a Gradio UI"
        run:
          command: "python app.py"
        ui:
          type: web
          port: 7860
          startup_wait_seconds: 15
        completion_signals:
          - "running on local url"
        timeout_seconds: 120
        """)
    )
    cfg = load_demo_config(str(tmp_path))
    assert cfg["ui"]["type"] == "web"
    assert cfg["ui"]["port"] == 7860
    assert cfg["ui"]["startup_wait_seconds"] == 15
    assert cfg["timeout_seconds"] == 120
