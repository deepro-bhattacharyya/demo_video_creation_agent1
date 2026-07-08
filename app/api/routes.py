"""FastAPI entrypoint: request a demo video for a given agent."""

from fastapi import FastAPI
from pydantic import BaseModel

from app.agent.graph import build_graph

app = FastAPI(title="DemoVideoBot")
graph = build_graph()


class VideoRequest(BaseModel):
    agent_id: str
    project_id: str
    custom_instructions: str = ""


@app.post("/videos")
def create_video(req: VideoRequest):
    # TODO (Milestone 7): invoke the graph; handle the review interrupt.
    result = graph.invoke({
        "agent_id": req.agent_id,
        "project_id": req.project_id,
        "custom_instructions": req.custom_instructions,
    })
    return {
        "narrated_video_path": result.get("narrated_video_path"),
        "silent_video_path": result.get("silent_video_path"),
        "status": result.get("status"),
    }


@app.get("/health")
def health():
    return {"status": "ok"}
