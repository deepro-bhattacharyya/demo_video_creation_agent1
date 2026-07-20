"""Shared state passed between every node in the pipeline.

Each node receives this dict (LangGraph handles the plumbing) and returns a
dict of the fields it wants to update. Keep it flat and simple.
"""

from typing import TypedDict


class VideoState(TypedDict, total=False):
    # --- Input ---
    source_type: str         # "hub" (default) | "standalone"
    agent_name: str          # display name, e.g. "Defect Triage (CrewAI)"
    project_name: str        # display name, e.g. "Dev test project"
    agent_folder: str        # absolute path to local agent folder (standalone only)

    # --- Fetched from the platform ---
    agent_display_name: str  # canonical name as shown in the platform
    agent_spec: str          # the agent's documentation / spec text
    run_id: str
    run_transcript: list[dict]   # structured step/HITL events from the run

    # --- Capture ---
    raw_video_path: str      # full screen recording of the run

    # --- Script ---
    scenes: list[dict]       # [{"start", "end", "on_screen", "narration"}]
    custom_instructions: str # optional per-client asks (naming, tone, focus)
    script_status: str       # "pending_review" | "approved"

    # --- Audio ---
    narration_audio_path: str

    # --- Outputs ---
    narrated_video_path: str
    silent_video_path: str
    status: str

    # --- Progress tracking ---
    completed_steps: list[str]   # node names that have finished, in order
