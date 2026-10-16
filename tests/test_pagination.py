from fastapi.testclient import TestClient

from tests.helpers import create_task


def test_list_defaults_to_the_first_page_of_twenty(client: TestClient) -> None:
    created = [create_task(client, title=f"Task {n}") for n in range(3)]

    page = client.get("/tasks").json()

    assert page == {
        "items": created,
        "total": 3,
        "limit": 20,
        "offset": 0,
        "next_offset": None,
        "previous_offset": None,
    }


def test_limit_and_offset_walk_through_the_pages(client: TestClient) -> None:
    created = [create_task(client, title=f"Task {n}") for n in range(5)]
    ids = [task["id"] for task in created]

    first = client.get("/tasks", params={"limit": 2}).json()
    second = client.get("/tasks", params={"limit": 2, "offset": first["next_offset"]}).json()
    third = client.get("/tasks", params={"limit": 2, "offset": second["next_offset"]}).json()

    assert [task["id"] for task in first["items"]] == ids[0:2]
    assert (first["total"], first["next_offset"], first["previous_offset"]) == (5, 2, None)
    assert [task["id"] for task in second["items"]] == ids[2:4]
    assert (second["next_offset"], second["previous_offset"]) == (4, 0)
    assert [task["id"] for task in third["items"]] == ids[4:5]
    assert (third["next_offset"], third["previous_offset"]) == (None, 2)


def test_offset_past_the_end_returns_an_empty_page(client: TestClient) -> None:
    create_task(client)

    page = client.get("/tasks", params={"limit": 5, "offset": 10}).json()

    assert page["items"] == []
    assert page["total"] == 1
    assert page["next_offset"] is None
    assert page["previous_offset"] == 5


def test_total_counts_only_tasks_matching_the_filter(client: TestClient) -> None:
    done = create_task(client, title="Done")
    create_task(client, title="Pending one")
    create_task(client, title="Pending two")
    client.patch(f"/tasks/{done['id']}", json={"completed": True})

    page = client.get("/tasks", params={"completed": "false", "limit": 1}).json()

    assert page["total"] == 2
    assert [task["title"] for task in page["items"]] == ["Pending one"]
    assert page["next_offset"] == 1
