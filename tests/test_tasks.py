def create_and_login_user(client, email):
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123!"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "StrongPassword123!"
        }
    )

    return response.json()["access_token"]


def test_create_task(client):
    token = create_and_login_user(
        client, "taskuser@example.com"
    )

    response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Learn automated testing",
            "description": "Write tests using pytest",
            "priority": "high"
        }
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Learn automated testing"
    assert response.json()["priority"] == "high"
    assert response.json()["completed"] is False


def test_get_all_tasks(client):
    token = create_and_login_user(
        client, "taskuser@example.com"
    )

    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/tasks",
        headers=headers,
        json={"title": "Task 1", "priority": "high"}
    )

    client.post(
        "/tasks",
        headers=headers,
        json={"title": "Task 2", "priority": "low"}
    )

    response = client.get("/tasks", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_single_task(client):
    token = create_and_login_user(
        client, "taskuser@example.com"
    )

    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/tasks",
        headers=headers,
        json={"title": "My task"}
    )

    task_id = create_response.json()["id"]

    response = client.get(
        f"/tasks/{task_id}",
        headers=headers
    )

    assert response.status_code == 200
    assert response.json()["title"] == "My task"


def test_get_nonexistent_task(client):
    token = create_and_login_user(
        client, "taskuser@example.com"
    )

    response = client.get(
        "/tasks/9999",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


def test_update_task(client):
    token = create_and_login_user(
        client, "taskuser@example.com"
    )

    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Original title"}
    )

    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        headers=headers,
        json={
            "title": "Updated title",
            "completed": True
        }
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"
    assert response.json()["completed"] is True


def test_delete_task(client):
    token = create_and_login_user(
        client, "taskuser@example.com"
    )

    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Task to delete"}
    )

    task_id = create_response.json()["id"]

    response = client.delete(
        f"/tasks/{task_id}",
        headers=headers
    )

    assert response.status_code == 204

    # Confirm task no longer exists
    get_response = client.get(
        f"/tasks/{task_id}",
        headers=headers
    )

    assert get_response.status_code == 404


def test_user_cannot_access_another_users_task(client):
    token1 = create_and_login_user(
        client, "user1@example.com"
    )

    token2 = create_and_login_user(
        client, "user2@example.com"
    )

    response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {token1}"},
        json={"title": "Private task"}
    )

    task_id = response.json()["id"]

    response = client.get(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )

    assert response.status_code == 404


def test_user_cannot_update_another_users_task(client):
    token1 = create_and_login_user(
        client, "user1@example.com"
    )

    token2 = create_and_login_user(
        client, "user2@example.com"
    )

    create_response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {token1}"},
        json={"title": "Private task"}
    )

    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token2}"},
        json={"title": "Hacked title"}
    )

    assert response.status_code == 404


def test_user_cannot_delete_another_users_task(client):
    token1 = create_and_login_user(
        client, "user1@example.com"
    )

    token2 = create_and_login_user(
        client, "user2@example.com"
    )

    create_response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {token1}"},
        json={"title": "Private task"}
    )

    task_id = create_response.json()["id"]

    response = client.delete(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )

    assert response.status_code == 404


def test_user_sees_only_their_own_tasks(client):
    token1 = create_and_login_user(
        client, "user1@example.com"
    )

    token2 = create_and_login_user(
        client, "user2@example.com"
    )

    client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {token1}"},
        json={"title": "User 1 task"}
    )

    client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {token2}"},
        json={"title": "User 2 task"}
    )

    response = client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {token1}"}
    )

    assert response.status_code == 200

    tasks = response.json()

    assert len(tasks) == 1
    assert tasks[0]["title"] == "User 1 task"