from fastapi.testclient import TestClient

from app.main import app


def test_can_create_and_list_tasks():
    with TestClient(app) as client:
        # create
        payload = {"title": "Write CI and tests"}
        r = client.post("/tasks", json=payload)
        assert r.status_code == 200
        created = r.json()
        assert created["id"] >= 1
        assert created["title"] == payload["title"]

        # list
        r = client.get("/tasks")
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert any(t["title"] == payload["title"] for t in items)
