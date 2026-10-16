from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage import get_repository
from tests.helpers import create_task

BLANK_TITLE = {"detail": "title: String should have at least 1 character"}


def test_create_rejects_blank_title(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "   "})

    assert response.status_code == 422
    assert response.json() == BLANK_TITLE


def test_create_rejects_missing_title(client: TestClient) -> None:
    response = client.post("/tasks", json={"description": "no title"})

    assert response.status_code == 422
    assert response.json() == {"detail": "title: Field required"}


def test_create_rejects_unknown_fields(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "Ok", "id": str(uuid4())})

    assert response.status_code == 422
    assert response.json() == {"detail": "id: Extra inputs are not permitted"}


def test_create_rejects_malformed_json(client: TestClient) -> None:
    response = client.post(
        "/tasks", content=b"{not json", headers={"content-type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "body: JSON decode error"}


def test_create_rejects_missing_body(client: TestClient) -> None:
    response = client.post("/tasks")

    assert response.status_code == 422
    assert response.json() == {"detail": "body: Field required"}


def test_patch_rejects_blank_title(client: TestClient) -> None:
    created = create_task(client)

    response = client.patch(f"/tasks/{created['id']}", json={"title": "   "})

    assert response.status_code == 422
    assert response.json() == BLANK_TITLE
    assert client.get(f"/tasks/{created['id']}").json() == created


@pytest.mark.parametrize("field", ["title", "completed"])
def test_patch_rejects_null_for_fields_that_cannot_be_cleared(
    client: TestClient, field: str
) -> None:
    created = create_task(client)

    response = client.patch(f"/tasks/{created['id']}", json={field: None})

    assert response.status_code == 422
    assert response.json() == {"detail": f"{field}: Value error, cannot be null"}
    assert client.get(f"/tasks/{created['id']}").json() == created


def test_patch_rejects_unknown_fields(client: TestClient) -> None:
    created = create_task(client)

    response = client.patch(f"/tasks/{created['id']}", json={"titel": "typo"})

    assert response.status_code == 422
    assert response.json() == {"detail": "titel: Extra inputs are not permitted"}


def test_malformed_task_id_is_422(client: TestClient) -> None:
    response = client.get("/tasks/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["detail"].startswith("task_id: Input should be a valid UUID")


def test_non_boolean_completed_filter_is_422(client: TestClient) -> None:
    response = client.get("/tasks", params={"completed": "maybe"})

    assert response.status_code == 422
    assert response.json() == {
        "detail": "completed: Input should be a valid boolean, unable to interpret input"
    }


def test_unknown_route_returns_custom_404(client: TestClient) -> None:
    response = client.get("/nope")

    assert response.status_code == 404
    assert response.json() == {"detail": "No route matches GET /nope"}


def test_unsupported_method_returns_405_with_allow_header(client: TestClient) -> None:
    response = client.put(f"/tasks/{uuid4()}", json={})

    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed"}
    assert "allow" in response.headers


def test_unhandled_error_returns_500_in_the_same_shape() -> None:
    app = create_app()

    def broken_repository() -> None:
        raise RuntimeError("storage is down")

    app.dependency_overrides[get_repository] = broken_repository
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/tasks")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


@pytest.mark.parametrize(
    ("params", "detail"),
    [
        ({"limit": 0}, "limit: Input should be greater than or equal to 1"),
        ({"limit": 101}, "limit: Input should be less than or equal to 100"),
        ({"offset": -1}, "offset: Input should be greater than or equal to 0"),
    ],
)
def test_out_of_range_pagination_params_are_422(
    client: TestClient, params: dict[str, int], detail: str
) -> None:
    response = client.get("/tasks", params=params)

    assert response.status_code == 422
    assert response.json() == {"detail": detail}
