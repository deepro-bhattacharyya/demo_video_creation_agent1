"""FastAPI entrypoint: request a demo video for a given agent."""

import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.agent.graph import build_graph

app = FastAPI(title="DemoVideoBot")

# MemorySaver keeps graph state in memory so interrupted runs can be resumed.
# Swap for a persistent checkpointer (e.g. SqliteSaver) before multi-worker deploy.
_checkpointer = MemorySaver()
graph = build_graph(checkpointer=_checkpointer)


class VideoRequest(BaseModel):
    agent_id: str
    project_id: str
    custom_instructions: str = ""


class ReviewDecision(BaseModel):
    action: str           # "approve" or "edit"
    scenes: list[dict] = []   # required when action == "edit"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/videos")
def create_video(req: VideoRequest):
    """Start the pipeline for a given agent. Returns immediately with a
    thread_id if the graph pauses at the human review step."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = graph.invoke(
        {
            "agent_id": req.agent_id,
            "project_id": req.project_id,
            "custom_instructions": req.custom_instructions,
        },
        config=config,
    )

    # If the graph is still running (paused at review_script interrupt),
    # state.next will be non-empty.
    snapshot = graph.get_state(config)
    if snapshot.next:
        return {
            "thread_id": thread_id,
            "status": "awaiting_review",
            "scenes": result.get("scenes", []),
            "custom_instructions": result.get("custom_instructions", ""),
        }

    return {
        "thread_id": thread_id,
        "narrated_video_path": result.get("narrated_video_path"),
        "silent_video_path": result.get("silent_video_path"),
        "status": result.get("status"),
    }


@app.post("/videos/{thread_id}/resume")
def resume_video(thread_id: str, decision: ReviewDecision):
    """Resume a pipeline that is paused at the review step.

    Send action="approve" to accept the current scenes, or action="edit"
    with an updated scenes list to revise and re-review.
    """
    config = {"configurable": {"thread_id": thread_id}}

    snapshot = graph.get_state(config)
    if not snapshot.next:
        raise HTTPException(status_code=404, detail="Thread not found or already completed.")

    resume_value: dict = {"action": decision.action}
    if decision.action == "edit":
        resume_value["scenes"] = decision.scenes

    result = graph.invoke(Command(resume=resume_value), config=config)

    # May be paused again if the user edited and the script loops back.
    snapshot = graph.get_state(config)
    if snapshot.next:
        return {
            "thread_id": thread_id,
            "status": "awaiting_review",
            "scenes": result.get("scenes", []),
        }

    return {
        "thread_id": thread_id,
        "narrated_video_path": result.get("narrated_video_path"),
        "silent_video_path": result.get("silent_video_path"),
        "status": result.get("status"),
    }


@app.get("/health")
def health():
    return {"status": "ok"}
