def register_manager(client):
    response = client.post(
        "/api/auth/register",
        json={
            "nonprofit_id": 1,
            "full_name": "Test Manager",
            "email": "manager@test.org",
            "password": "SecurePass123!",
            "role": "manager",
        },
    )

    return response


def create_nonprofit(client):
    response = client.post(
        "/api/nonprofits",
        json={
            "name": "Test Nonprofit",
            "registration_number": "AUTH-NP-001",
            "email": "finance@auth-test.org",
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def test_register_user(client):
    nonprofit_id = create_nonprofit(client)

    response = client.post(
        "/api/auth/register",
        json={
            "nonprofit_id": nonprofit_id,
            "full_name": "Test Manager",
            "email": "manager@test.org",
            "password": "SecurePass123!",
            "role": "manager",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "manager@test.org"
    assert data["role"] == "manager"
    assert data["is_active"] is True

    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_registration_is_rejected(client):
    nonprofit_id = create_nonprofit(client)

    payload = {
        "nonprofit_id": nonprofit_id,
        "full_name": "Test Manager",
        "email": "manager@test.org",
        "password": "SecurePass123!",
        "role": "manager",
    }

    first_response = client.post(
        "/api/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/api/auth/register",
        json=payload,
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == (
        "Email is already registered"
    )


def test_login_returns_access_token(client):
    nonprofit_id = create_nonprofit(client)

    client.post(
        "/api/auth/register",
        json={
            "nonprofit_id": nonprofit_id,
            "full_name": "Test Manager",
            "email": "manager@test.org",
            "password": "SecurePass123!",
            "role": "manager",
        },
    )

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
    assert len(data["access_token"]) > 20


def test_wrong_password_is_rejected(client):
    nonprofit_id = create_nonprofit(client)

    client.post(
        "/api/auth/register",
        json={
            "nonprofit_id": nonprofit_id,
            "full_name": "Test Manager",
            "email": "manager@test.org",
            "password": "SecurePass123!",
            "role": "manager",
        },
    )

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


def test_authenticated_user_can_access_me(client):
    nonprofit_id = create_nonprofit(client)

    client.post(
        "/api/auth/register",
        json={
            "nonprofit_id": nonprofit_id,
            "full_name": "Test Manager",
            "email": "manager@test.org",
            "password": "SecurePass123!",
            "role": "manager",
        },
    )

    login_response = client.post(
        "/api/auth/token",
        data={
            "username": "manager@test.org",
            "password": "SecurePass123!",
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
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