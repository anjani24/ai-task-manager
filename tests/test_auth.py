from app.auth import hash_refresh_token
from app.models import RefreshToken

def register_user(client, email="test@example.com"):
    return client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123!"
        }
    )


def login_user(client, email="test@example.com"):
    return client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "StrongPassword123!"
        }
    )


def test_register_user(client):
    response = register_user(client)

    assert response.status_code == 201

    data = response.json()

    # Adapt these assertions to your actual response structure
    assert data["message"] == "User registered successfully"
    assert data["user"]["email"] == "test@example.com"
    assert "password_hash" not in data["user"]


def test_duplicate_registration(client):
    register_user(client)

    response = register_user(client)

    assert response.status_code == 400


def test_login_user(client):
    register_user(client)

    response = login_user(client)

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_with_wrong_password(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "WrongPassword123!"
        }
    )

    assert response.status_code == 401


def test_login_with_unknown_email(client):
    response = login_user(client)

    assert response.status_code == 401


def test_get_current_user(client):
    register_user(client)
    login_response = login_user(client)

    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_access_protected_endpoint_without_token(client):
    response = client.get("/auth/me")

    assert response.status_code in (401, 403)



def test_refresh_token(client, db):
    register_user(client)
    login_response = login_user(client)

    old_refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh_token}
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != old_refresh_token

    # Hash both tokens to find their database records
    old_hash = hash_refresh_token(old_refresh_token)
    new_hash = hash_refresh_token(data["refresh_token"])

    old_record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == old_hash
    ).first()

    new_record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == new_hash
    ).first()

    # Both tokens must belong to the same family
    assert old_record.family_id == new_record.family_id

    # Old token must be revoked
    assert old_record.revoked_at is not None

    # Old token must point to its replacement
    assert old_record.replaced_by_id == new_record.id

def test_old_refresh_token_cannot_be_reused(client):
    register_user(client)
    login_response = login_user(client)

    old_refresh_token = login_response.json()["refresh_token"]

    client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh_token}
    )

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh_token}
    )

    assert response.status_code == 401


def test_logout(client):
    register_user(client)
    login_response = login_user(client)

    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200


def test_revoked_refresh_token_cannot_be_used(client):
    register_user(client)
    login_response = login_user(client)

    refresh_token = login_response.json()["refresh_token"]

    client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token}
    )

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert response.status_code == 401


def test_refresh_token_reuse_revokes_family(client, db):
    register_user(client)
    login_response = login_user(client)

    old_refresh_token = login_response.json()["refresh_token"]

    # First refresh: R1 becomes R2
    first_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh_token}
    )

    assert first_refresh.status_code == 200

    new_refresh_token = first_refresh.json()["refresh_token"]

    # Reuse the old token R1
    reuse_response = client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh_token}
    )

    assert reuse_response.status_code == 401

    # Find R2 in the database
    new_hash = hash_refresh_token(new_refresh_token)

    new_record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == new_hash
    ).first()

    # R2 should also be revoked
    assert new_record.revoked_at is not None