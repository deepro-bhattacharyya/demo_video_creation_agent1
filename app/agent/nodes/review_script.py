"""Pause for a human to approve or edit the script before rendering."""

from langgraph.types import interrupt

from app.agent.state import VideoState


def review_script(state: VideoState) -> dict:
    # TODO (Milestone 4):
    #   - interrupt() with the scenes + custom_instructions for review
    #   - on "edit": return updated scenes, stay "pending_review" (loops back)
    #   - on "approve": return {"script_status": "approved"}
    #   - support a timeout / skip-review flag for standard runs
    decision = interrupt({
        "scenes": state.get("scenes", []),
        "custom_instructions": state.get("custom_instructions", ""),
    })
    if decision.get("action") == "edit":
        return {"scenes": decision["scenes"], "script_status": "pending_review"}
    return {"script_status": "approved"}
