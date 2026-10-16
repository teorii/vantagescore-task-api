from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from tests.helpers import create_task


def test_create_task_returns_201_with_generated_fields(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "Write tests", "description": "pytest"})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Write tests"
    assert body["description"] == "pytest"
    assert body["completed"] is False
    UUID(body["id"])
    assert datetime.fromisoformat(body["created_at"]).tzinfo is not None
    assert client.get(f"/tasks/{body['id']}").json() == body


def test_create_task_points_location_header_at_the_new_task(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "Locate me"})

    assert response.headers["location"].endswith(f"/tasks/{response.json()['id']}")
    assert client.get(response.headers["location"]).status_code == 200


def test_create_task_strips_whitespace_around_title(client: TestClient) -> None:
    assert create_task(client, title="  Padded  ")["title"] == "Padded"


def test_get_missing_task_returns_404(client: TestClient) -> None:
    task_id = uuid4()

    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Task {task_id} not found"}


def test_patch_completed_marks_task_done(client: TestClient) -> None:
    created = create_task(client, title="Ship it")

    response = client.patch(f"/tasks/{created['id']}", json={"completed": True})

    assert response.status_code == 200
    body = response.json()
    assert body["completed"] is True
    assert body["id"] == created["id"]
    assert body["title"] == "Ship it"
    assert body["created_at"] == created["created_at"]
    assert client.get(f"/tasks/{created['id']}").json()["completed"] is True


def test_patch_missing_task_returns_404(client: TestClient) -> None:
    task_id = uuid4()

    response = client.patch(f"/tasks/{task_id}", json={"completed": True})

    assert response.status_code == 404
    assert response.json() == {"detail": f"Task {task_id} not found"}


def test_patch_with_empty_body_changes_nothing(client: TestClient) -> None:
    created = create_task(client)

    response = client.patch(f"/tasks/{created['id']}", json={})

    assert response.status_code == 200
    assert response.json() == created


def test_patch_description_null_clears_it(client: TestClient) -> None:
    created = create_task(client, description="temporary")

    response = client.patch(f"/tasks/{created['id']}", json={"description": None})

    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["title"] == created["title"]


def test_delete_returns_204_with_no_body_then_404(client: TestClient) -> None:
    created = create_task(client)

    response = client.delete(f"/tasks/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert "content-type" not in response.headers
    assert client.get(f"/tasks/{created['id']}").status_code == 404
    assert client.delete(f"/tasks/{created['id']}").status_code == 404


def test_list_returns_tasks_in_creation_order(client: TestClient) -> None:
    first = create_task(client, title="First")
    second = create_task(client, title="Second")

    response = client.get("/tasks")

    assert response.status_code == 200
    assert [task["id"] for task in response.json()["items"]] == [first["id"], second["id"]]


def test_list_filters_by_completed(client: TestClient) -> None:
    pending = create_task(client, title="Pending")
    done = create_task(client, title="Done")
    client.patch(f"/tasks/{done['id']}", json={"completed": True})

    completed_only = client.get("/tasks", params={"completed": "true"}).json()["items"]
    pending_only = client.get("/tasks", params={"completed": "false"}).json()["items"]

    assert [task["id"] for task in completed_only] == [done["id"]]
    assert [task["id"] for task in pending_only] == [pending["id"]]


def test_create_and_delete_append_to_event_log(client: TestClient, event_log: Path) -> None:
    created = create_task(client)
    client.delete(f"/tasks/{created['id']}")

    lines = event_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0].endswith(f"created {created['id']}")
    assert lines[1].endswith(f"deleted {created['id']}")
    datetime.fromisoformat(lines[0].split(" ")[0])
