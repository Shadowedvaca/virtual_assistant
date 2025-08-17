from fastapi.testclient import TestClient

from app.main import app


def setup_seed_tasks(client: TestClient):
    payloads = [
        {"title": "Send weekly status report to Alice"},
        {"title": "Send status report"},
        {"title": "Buy milk"},
        {"title": "Buy whole milk at the store"},
        {"title": "Plan and draft and send Q3 report"},
    ]
    ids = []
    for p in payloads:
        r = client.post("/tasks", json=p)
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])
    return ids


def test_suggestions_combine_and_split():
    with TestClient(app) as client:
        setup_seed_tasks(client)
        r = client.get("/suggestions", params={"threshold": 0.3, "top_k": 10, "include_split": True})
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list) and len(data) > 0

        kinds = {d["type"] for d in data}
        assert "combine" in kinds
        assert "split" in kinds

        combine = next(d for d in data if d["type"] == "combine")
        assert isinstance(combine["task_ids"], list) and len(combine["task_ids"]) == 2
        assert 0.0 <= combine["score"] <= 1.0

        split = next(d for d in data if d["type"] == "split")
        assert isinstance(split["subtasks"], list) and len(split["subtasks"]) >= 2
