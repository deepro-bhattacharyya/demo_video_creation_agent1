"""Pause for a human to approve or edit the script before rendering.

Set SKIP_REVIEW=true in .env to auto-approve and skip this step entirely
(useful for batch runs or re-renders where the script is already known-good).
"""

from langgraph.types import interrupt

from app import config
from app.agent.state import VideoState


def review_script(state: VideoState) -> dict:
    # Auto-approve path — no human pause needed.
    if config.SKIP_REVIEW:
        return {
            "script_status": "approved",
            "completed_steps": state.get("completed_steps", []) + ["review_script"],
        }

    # Surface the current scenes and any client instructions for human review.
    decision = interrupt({
        "scenes": state.get("scenes", []),
        "custom_instructions": state.get("custom_instructions", ""),
    })

    # "edit": caller supplies updated scenes → loop back through generate_script
    # for re-approval with the revised content.
    if decision.get("action") == "edit":
        return {
            "scenes": decision["scenes"],
            "script_status": "pending_review",
            "completed_steps": state.get("completed_steps", []) + ["review_script"],
        }

    # "approve" (or any other value): accept the current scenes as-is.
    return {
        "script_status": "approved",
        "completed_steps": state.get("completed_steps", []) + ["review_script"],
    }
