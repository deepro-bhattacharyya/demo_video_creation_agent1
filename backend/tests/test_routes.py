"""API smoke tests.

POST /videos now returns immediately with {thread_id, status: "running"}.
GET  /videos/{id}/status is polled for progress.
POST /videos/{id}/resume resumes after review.
"""

from fastapi.testclient import TestClient

from app.api.routes import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_video_returns_thread_id():
    response = client.post(
        "/videos",
        json={"agent_name": "Test Agent", "project_name": "Test Project"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "thread_id" in data
    assert data["status"] == "running"


def test_status_returns_running_for_new_job():
    start = client.post(
        "/videos",
        json={"agent_name": "Test Agent", "project_name": "Test Project"},
    )
    thread_id = start.json()["thread_id"]

    status = client.get(f"/videos/{thread_id}/status")
    assert status.status_code == 200
    assert status.json()["thread_id"] == thread_id


def test_status_404_for_unknown_thread():
    response = client.get("/videos/nonexistent-thread/status")
    assert response.status_code == 404


def test_resume_404_for_unknown_thread():
    response = client.post(
        "/videos/nonexistent-thread/resume",
        json={"action": "approve"},
    )
    assert response.status_code == 404


def test_resume_400_when_job_not_awaiting_review():
    start = client.post(
        "/videos",
        json={"agent_name": "Test Agent", "project_name": "Test Project"},
    )
    thread_id = start.json()["thread_id"]

    # Job is in "running" state, not "awaiting_review"
    response = client.post(
        f"/videos/{thread_id}/resume",
        json={"action": "approve"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Standalone mode routes
# ---------------------------------------------------------------------------

def test_create_video_standalone_mode_returns_thread_id():
    response = client.post(
        "/videos",
        json={
            "source_type": "standalone",
            "agent_folder": "C:/fake/agent",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "thread_id" in data
    assert data["status"] == "running"


def test_create_video_standalone_missing_folder_returns_422():
    response = client.post(
        "/videos",
        json={"source_type": "standalone"},
    )
    assert response.status_code == 422


def test_create_video_hub_mode_unchanged():
    response = client.post(
        "/videos",
        json={
            "source_type": "hub",
            "agent_name": "Test Agent",
            "project_name": "Test Project",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_create_video_default_source_type_is_hub():
    """Omitting source_type should behave exactly like source_type='hub'."""
    response = client.post(
        "/videos",
        json={"agent_name": "Test Agent", "project_name": "Test Project"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "running"
