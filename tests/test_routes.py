"""Basic API smoke tests — no pipeline execution involved."""

from fastapi.testclient import TestClient

from app.api.routes import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_resume_unknown_thread_returns_404():
    response = client.post(
        "/videos/nonexistent-thread-id/resume",
        json={"action": "approve"},
    )
    assert response.status_code == 404
