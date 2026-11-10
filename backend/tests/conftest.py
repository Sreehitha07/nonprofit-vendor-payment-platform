import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.nonprofit import Nonprofit
from app.models.user import User


TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def manager_account(client):
    db = TestingSessionLocal()

    nonprofit = Nonprofit(
        name="Community Hope Foundation",
        registration_number="TEST-NP-001",
        email="finance@test.org",
    )

    db.add(nonprofit)
    db.flush()

    manager = User(
        nonprofit_id=nonprofit.id,
        vendor_id=None,
        full_name="Test Manager",
        email="manager@test.org",
        password_hash=hash_password(
            "SecurePass123!"
        ),
        role="manager",
        is_active=True,
    )

    db.add(manager)
    db.commit()

    nonprofit_id = nonprofit.id

    db.close()

    login_response = client.post(
        "/api/auth/token",
        data={
            "username": "manager@test.org",
            "password": "SecurePass123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "nonprofit_id": nonprofit_id,
        "headers": {
            "Authorization": f"Bearer {token}"
        },
    }


@pytest.fixture()
def nonprofit_and_vendor(
    client,
    manager_account,
):
    nonprofit_id = manager_account["nonprofit_id"]
    headers = manager_account["headers"]

    response = client.post(
        "/api/vendors",
        headers=headers,
        json={
            "name": "Bright Start Childcare",
            "contact_name": "Jane Smith",
            "email": "billing@brightstart.org",
            "status": "active",
            "nonprofit_id": nonprofit_id,
        },
    )

    assert response.status_code == 201

    vendor_id = response.json()["id"]

    return nonprofit_id, vendor_id, headers