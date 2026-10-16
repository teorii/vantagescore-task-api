from typing import Any

from fastapi.testclient import TestClient


def create_task(client: TestClient, title: str = "Write tests", **fields: Any) -> dict[str, Any]:
    """Create a task through the API and return the response body."""
    response = client.post("/tasks", json={"title": title, **fields})
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body
