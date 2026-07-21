"""Set dummy env vars before any test module imports app.config.

app.config runs _require() at import time, so these must be set here
(in conftest.py, which pytest loads first) rather than in fixtures.
Real values from a local .env take precedence via load_dotenv(); these
defaults only apply when .env is absent (e.g. CI).
"""

import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("AGENTICQEAHUB_BASE_URL", "http://localhost")
os.environ.setdefault("HUB_EMAIL", "test@test.com")
os.environ.setdefault("HUB_PASSWORD", "testpass")
