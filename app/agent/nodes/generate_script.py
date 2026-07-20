"""Ask Gemini to turn the agent spec + run transcript into a timed scene list.

Gemini is called once per pipeline run (TTS is handled by edge-tts, not Gemini).
Free tier (1,500 req/day) is sufficient for normal use at that rate.

LangGraph retries this node up to 3 times (see graph.py) so any exception
— bad JSON, empty response, failed validation — triggers an automatic retry.
"""

import json
import time

import structlog
from google import genai
from google.genai import types

from app import config
from app.agent.state import VideoState

log = structlog.get_logger()
_MODEL       = "gemini-2.0-flash"
_MAX_RETRIES = 4          # total attempts = 1 + 4 retries
_RETRY_BASE  = 35         # seconds — matches Gemini's suggested retryDelay


def generate_script(state: VideoState) -> dict:
    log.info("generate_script.start", agent=state.get("agent_name"))
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    prompt = _build_prompt(state["agent_spec"], state["run_transcript"])

    response = _call_with_retry(client, prompt)

    scenes = _parse_and_validate(response.text)

    log.info("generate_script.done", agent=state.get("agent_name"), scene_count=len(scenes))
    return {
        "scenes": scenes,
        "script_status": "pending_review",
        "status": "scripted",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call_with_retry(client, prompt: str):
    """Call Gemini with exponential back-off on rate-limit (429) errors.

    With TTS moved to edge-tts, Gemini is only called once per pipeline run.
    The free tier (1,500 req/day) is unlikely to be exhausted at that rate.
    Retries still handle transient RPM spikes gracefully.
    """
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return client.models.generate_content(
                model=_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
        except Exception as exc:
            err = str(exc)
            is_rate_limit = (
                "429" in err
                or "RESOURCE_EXHAUSTED" in err
                or "quota" in err.lower()
                or "rate" in err.lower()
            )
            if is_rate_limit and attempt < _MAX_RETRIES:
                wait = _RETRY_BASE * (2 ** attempt)   # 35s, 70s, 140s, 280s
                log.warning(
                    "generate_script.rate_limit",
                    attempt=attempt + 1,
                    wait_seconds=wait,
                    error=err[:120],
                )
                time.sleep(wait)
                continue
            raise


def _build_prompt(agent_spec: str, run_transcript: list[dict]) -> str:
    transcript_text = "\n".join(
        f"[{e.get('timestamp', '')}] {e.get('type', 'step')}: {e.get('content', '')}"
        for e in run_transcript
    )
    return f"""You are writing a narration script for a demo video of an AI agent.

## Agent Specification
{agent_spec}

## Run Transcript
{transcript_text}

## Task
Produce a timed scene list for the demo video. Each scene describes what is
happening on screen and provides a narrator line that explains it clearly to a
viewer who has never seen this agent before.

Return a JSON array. Each element must have exactly these four fields:
- "start": scene start time in seconds (number, >= 0)
- "end":   scene end time in seconds (number, > start)
- "on_screen": short caption shown on the video (max 10 words)
- "narration": narrator sentence read aloud (1–3 clear, professional sentences)

Rules:
- Scenes must be in chronological order with no gaps and no overlaps.
- The first scene must start at 0.
- Every part of the run must be covered — do not skip steps.
- Narration must be factual: describe what the agent does, not what it "tries" to do.
- on_screen text must be short enough to read in under 3 seconds.

Return ONLY the JSON array — no markdown fences, no extra text.
"""


def _parse_and_validate(raw: str) -> list[dict]:
    """Parse JSON and check structural integrity. Raises on any problem."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    scenes: list[dict] = json.loads(text)

    if not isinstance(scenes, list) or len(scenes) == 0:
        raise ValueError("Gemini returned an empty or non-list scene array.")

    required = {"start", "end", "on_screen", "narration"}
    for i, scene in enumerate(scenes):
        missing = required - scene.keys()
        if missing:
            raise ValueError(f"Scene {i} is missing fields: {missing}")
        if scene["end"] <= scene["start"]:
            raise ValueError(
                f"Scene {i} has end ({scene['end']}) <= start ({scene['start']})."
            )

    for i in range(1, len(scenes)):
        if scenes[i]["start"] < scenes[i - 1]["end"]:
            raise ValueError(f"Scene {i} overlaps with scene {i - 1}.")

    if scenes[0]["start"] != 0:
        scenes[0]["start"] = 0

    return scenes
