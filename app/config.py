"""Central config. All secrets and settings load here from the environment.

Nothing else in the codebase should read os.environ directly — import from here.
This keeps every secret in one place and makes swapping keys trivial later.
"""

import os

from dotenv import load_dotenv

load_dotenv()  # reads .env in local dev; no-op in prod if vars are already set


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


# Gemini API key — used for both script generation (LLM) and TTS voice-over.
# Personal key for prototyping; swap for an org key before wider rollout (one-line change here).
GEMINI_API_KEY = _require("GEMINI_API_KEY")

# AgenticQEAHub platform
HUB_BASE_URL = _require("AGENTICQEAHUB_BASE_URL").rstrip("/")
HUB_EMAIL = _require("HUB_EMAIL")
HUB_PASSWORD = _require("HUB_PASSWORD")

# Output location
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./output")

# Set to true to skip the human review step and auto-approve scripts.
# Useful for batch/automated runs; leave false for first-time or client-specific videos.
SKIP_REVIEW = os.environ.get("SKIP_REVIEW", "false").lower() == "true"
