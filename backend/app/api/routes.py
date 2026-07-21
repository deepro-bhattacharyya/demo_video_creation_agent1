"""FastAPI entrypoint: request a demo video for a given agent."""

import os
import pathlib
import threading
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.agent.graph import build_graph

app = FastAPI(title="DemoVideoBot")

# Allow the React dev server to call the API in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_checkpointer = MemorySaver()
graph = build_graph(checkpointer=_checkpointer)

# In-memory job store: {thread_id: {status, ...payload}}
# Each thread_id has its own key so concurrent access doesn't collide.
_jobs: dict = {}
_jobs_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class VideoRequest(BaseModel):
    # Hub mode fields
    agent_name: str = ""
    project_name: str = ""
    custom_instructions: str = ""
    # Standalone mode fields
    source_type: str = "hub"    # "hub" | "standalone"
    agent_folder: str = ""      # absolute path to local agent folder (standalone only)


class ReviewDecision(BaseModel):
    action: str            # "approve" or "edit"
    scenes: list[dict] = []


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

def _run_graph(thread_id: str, input_state: dict) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = graph.invoke(input_state, config=config)
        snapshot = graph.get_state(config)
        with _jobs_lock:
            if snapshot.next:
                _jobs[thread_id] = {
                    "status": "awaiting_review",
                    "scenes": result.get("scenes", []),
                    "custom_instructions": result.get("custom_instructions", ""),
                }
            else:
                _jobs[thread_id] = {
                    "status": "done",
                    "narrated_video_path": result.get("narrated_video_path"),
                    "silent_video_path": result.get("silent_video_path"),
                }
    except Exception as exc:
        with _jobs_lock:
            _jobs[thread_id] = {"status": "error", "error": str(exc)}


def _resume_graph(thread_id: str, resume_value: dict) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = graph.invoke(Command(resume=resume_value), config=config)
        snapshot = graph.get_state(config)
        with _jobs_lock:
            if snapshot.next:
                _jobs[thread_id] = {
                    "status": "awaiting_review",
                    "scenes": result.get("scenes", []),
                    "custom_instructions": result.get("custom_instructions", ""),
                }
            else:
                _jobs[thread_id] = {
                    "status": "done",
                    "narrated_video_path": result.get("narrated_video_path"),
                    "silent_video_path": result.get("silent_video_path"),
                }
    except Exception as exc:
        with _jobs_lock:
            _jobs[thread_id] = {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/videos")
def create_video(req: VideoRequest):
    """Kick off the pipeline in a background thread and return a thread_id
    immediately. Poll GET /videos/{thread_id}/status to track progress."""
    thread_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[thread_id] = {"status": "running"}

    input_state: dict = {
        "source_type": req.source_type,
        "agent_name": req.agent_name,
        "project_name": req.project_name,
        "custom_instructions": req.custom_instructions,
    }
    if req.source_type == "standalone":
        if not req.agent_folder:
            raise HTTPException(
                status_code=422,
                detail="agent_folder is required when source_type is 'standalone'.",
            )
        input_state["agent_folder"] = req.agent_folder

    threading.Thread(
        target=_run_graph,
        args=(thread_id, input_state),
        daemon=True,
    ).start()

    return {"thread_id": thread_id, "status": "running"}


@app.get("/videos/{thread_id}/status")
def get_status(thread_id: str):
    """Return the current status of a pipeline job, plus per-step progress.

    completed_steps / current_node come from the LangGraph checkpoint so the
    UI can show live per-step ticks as each node finishes.
    """
    with _jobs_lock:
        job = _jobs.get(thread_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = graph.get_state(config)
        completed_steps = (
            snapshot.values.get("completed_steps", [])
            if snapshot and snapshot.values else []
        )
        current_node = snapshot.next[0] if snapshot and snapshot.next else None
    except Exception:
        completed_steps = []
        current_node = None

    return {
        "thread_id": thread_id,
        **job,
        "completed_steps": completed_steps,
        "current_node": current_node,
    }


@app.post("/videos/{thread_id}/resume")
def resume_video(thread_id: str, decision: ReviewDecision):
    """Resume a pipeline that is paused at the script-review step."""
    with _jobs_lock:
        job = _jobs.get(thread_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "awaiting_review":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not awaiting review (current status: {job['status']}).",
        )

    resume_value: dict = {"action": decision.action}
    if decision.action == "edit":
        resume_value["scenes"] = decision.scenes

    with _jobs_lock:
        _jobs[thread_id] = {"status": "running"}

    threading.Thread(
        target=_resume_graph,
        args=(thread_id, resume_value),
        daemon=True,
    ).start()

    return {"thread_id": thread_id, "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Serve the React build in production (mounted after all API routes)
# ---------------------------------------------------------------------------
def _find_frontend_dist() -> pathlib.Path | None:
    """Locate the built React app (frontend/dist) by walking up from this file.

    This keeps working regardless of nesting: locally the Python code lives under
    backend/app/... while frontend/ sits at the repo root, whereas in Docker app/
    and frontend/ sit side by side under /app. Searching upward finds it in both.
    """
    for base in pathlib.Path(__file__).resolve().parents:
        candidate = base / "frontend" / "dist"
        if candidate.is_dir():
            return candidate
    return None


_frontend_dist = _find_frontend_dist()

if _frontend_dist is not None:
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
