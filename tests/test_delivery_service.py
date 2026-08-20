from fastapi.testclient import TestClient

from media_delivery.delivery_service import app, get_logs


class RecordingLogs:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    def ingest(self, *, level: str, message: str, metadata: dict) -> dict:
        self.entries.append({"level": level, "message": message, "metadata": metadata})
        return {"event_id": "evt_demo"}

    def search(self, query: str) -> dict:
        return {"events": [entry for entry in self.entries if entry["metadata"]["order_id"] == query]}


def test_matching_media_becomes_searchable_creator_delivery() -> None:
    logs = RecordingLogs()
    app.dependency_overrides[get_logs] = lambda: logs
    client = TestClient(app)

    response = client.post(
        "/media-jobs",
        json={
            "asset_id": "asset_42",
            "creator_id": "creator_7",
            "order_id": "order_1001",
            "source_format": "mp4",
            "delivery_format": "mp4",
        },
    )
    found = client.get("/delivery-logs", params={"order_id": "order_1001"})

    assert response.status_code == 200
    assert response.json()["state"] == "ready_for_creator"
    assert found.json()["events"][0]["metadata"]["asset_id"] == "asset_42"
    app.dependency_overrides.clear()
