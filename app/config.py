"""Central config. All secrets and settings load here from the environment.

Nothing else in the codebase should read os.environ directly — import from here.
This keeps every secret in one place and makes swapping keys trivial later.
"""

import os
import ssl

from dotenv import load_dotenv

load_dotenv()  # reads .env in local dev; no-op in prod if vars are already set

# ---------------------------------------------------------------------------
# Windows certificate store integration
# ---------------------------------------------------------------------------
# Cognizant's network routes HTTPS through an SSL-inspection proxy whose root
# CA is pushed to every machine via Group Policy and lives in the Windows
# certificate store.  Python's default CA bundle (certifi) doesn't include it,
# so plain Python HTTPS calls (Gemini API via google-genai / httpx) fail with
# "certificate verify failed".
#
# truststore.inject_into_ssl() patches Python's ssl module to query the Windows
# store directly — the same CA list that Chrome, Edge and Windows itself trust.
# No certificates are disabled; full chain verification is preserved.
# ---------------------------------------------------------------------------
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    # truststore unavailable or failed (non-Windows CI, import error, etc.).
    # Fall back: honour DISABLE_SSL_VERIFY=true as a last resort escape hatch.
    if os.environ.get("DISABLE_SSL_VERIFY", "false").lower() in ("1", "true", "yes"):
        ssl._create_default_https_context = ssl._create_unverified_context  # type: ignore[attr-defined]
        try:
            import httpx as _httpx
            _orig  = _httpx.Client.__init__
            _aorig = _httpx.AsyncClient.__init__
            def _nv(self, *a, **kw):  kw.setdefault("verify", False); _orig(self, *a, **kw)   # type: ignore
            def _anv(self, *a, **kw): kw.setdefault("verify", False); _aorig(self, *a, **kw)  # type: ignore
            _httpx.Client.__init__      = _nv   # type: ignore[method-assign]
            _httpx.AsyncClient.__init__ = _anv  # type: ignore[method-assign]
        except ImportError:
            pass


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


# Gemini API key — used for script generation only (1 call per pipeline run).
# TTS is handled by edge-tts (free, no API key), so Gemini quota is used sparingly.
# Free tier (1,500 req/day) is sufficient for normal use.
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
