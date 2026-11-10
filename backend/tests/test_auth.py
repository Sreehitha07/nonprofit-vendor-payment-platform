def test_manager_can_create_staff_user(
    client,
    manager_account,
):
    response = client.post(
        "/api/auth/register",
        headers=manager_account["headers"],
        json={
            "nonprofit_id": manager_account[
                "nonprofit_id"
            ],
            "full_name": "Test Staff",
            "email": "staff@test.org",
            "password": "SecurePass123!",
            "role": "staff",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "staff@test.org"
    assert data["role"] == "staff"
    assert data["is_active"] is True

    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_registration_is_rejected(
    client,
    manager_account,
):
    payload = {
        "nonprofit_id": manager_account[
            "nonprofit_id"
        ],
        "full_name": "Test Staff",
        "email": "staff@test.org",
        "password": "SecurePass123!",
        "role": "staff",
    }

    first_response = client.post(
        "/api/auth/register",
        headers=manager_account["headers"],
        json=payload,
    )

    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/api/auth/register",
        headers=manager_account["headers"],
        json=payload,
    )

    assert duplicate_response.status_code == 409

    assert duplicate_response.json()["detail"] == (
        "Email is already registered"
    )


def test_login_returns_access_token(
    client,
    manager_account,
):
    response = client.post(
        "/api/auth/token",
        data={
            "username": "manager@test.org",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_wrong_password_is_rejected(
    client,
    manager_account,
):
    response = client.post(
        "/api/auth/token",
        data={
            "username": "manager@test.org",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401

    assert response.json()["detail"] == (
        "Incorrect email or password"
    )


def test_authenticated_user_can_access_me(
    client,
    manager_account,
):
    response = client.get(
        "/api/auth/me",
        headers=manager_account["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "manager@test.org"
    assert data["role"] == "manager"


def test_me_requires_authentication(client):
    response = client.get(
        "/api/auth/me"
    )

    assert response.status_code == 401


def test_manager_cannot_create_admin(
    client,
    manager_account,
):
    response = client.post(
        "/api/auth/register",
        headers=manager_account["headers"],
        json={
            "nonprofit_id": manager_account[
                "nonprofit_id"
            ],
            "full_name": "Unauthorized Admin",
            "email": "admin@test.org",
            "password": "SecurePass123!",
            "role": "admin",
        },
    )

    assert response.status_code == 403


def test_registration_requires_authentication(
    client,
    manager_account,
):
    response = client.post(
        "/api/auth/register",
        json={
            "nonprofit_id": manager_account[
                "nonprofit_id"
            ],
            "full_name": "Anonymous User",
            "email": "anonymous@test.org",
            "password": "SecurePass123!",
            "role": "staff",
        },
    )

    assert response.status_code == 401