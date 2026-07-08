"""Ask Gemini to turn the spec + run transcript into a timed scene list."""

from app.agent.state import VideoState


def generate_script(state: VideoState) -> dict:
    # TODO (Milestone 3):
    #   - build a prompt from state["agent_spec"] + state["run_transcript"]
    #   - require JSON: [{"start","end","on_screen","narration"}, ...]
    #   - parse safely; retry on bad JSON (graph sets max_attempts=3)
    raise NotImplementedError
    # return {"scenes": [...], "script_status": "pending_review", "status": "scripted"}
