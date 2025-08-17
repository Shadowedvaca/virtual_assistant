from fastapi.testclient import TestClient

from app.main import app


def seed_tasks(client: TestClient):
    for title in [
        "Send weekly status report to Alice",
        "Send status report",
        "Buy milk",
        "Buy whole milk at the store",
    ]:
        r = client.post("/tasks", json={"title": title})
        assert r.status_code == 200


def test_feedback_records_history():
    with TestClient(app) as client:
        seed_tasks(client)
        # Get suggestions
        r = client.get("/suggestions", params={"threshold": 0.3, "top_k": 10})
        assert r.status_code == 200
        suggestions = r.json()
        assert suggestions

        combo = next((s for s in suggestions if s["type"] == "combine"), None)
        assert combo is not None

        # Send feedback (accept combine)
        fb = {
            "id": combo["id"],
            "type": "combine",
            "accepted": True,
            "task_ids": combo["task_ids"],
            "reason": "Yes, these are duplicates",
        }
        r = client.post("/suggestions/feedback", json=fb)
        assert r.status_code == 200
        touched = r.json()["touched"]
        assert touched == combo["task_ids"]

        # Verify history written on at least one touched task
        task_id = touched[0]
        r = client.get(f"/tasks/{task_id}")
        assert r.status_code == 200
        hist = r.json().get("history")
        assert isinstance(hist, list) and any(h.get("id") == combo["id"] for h in hist)
