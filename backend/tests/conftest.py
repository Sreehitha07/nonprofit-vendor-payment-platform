import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.database import Base, get_db
from app.main import app


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
def nonprofit_and_vendor(client):
    nonprofit_response = client.post(
        "/api/nonprofits",
        json={
            "name": "Community Hope Foundation",
            "registration_number": "TEST-NP-001",
            "email": "finance@test.org",
        },
    )

    assert nonprofit_response.status_code == 201

    nonprofit_id = nonprofit_response.json()["id"]

    vendor_response = client.post(
        "/api/vendors",
        json={
            "name": "Bright Start Childcare",
            "contact_name": "Jane Smith",
            "email": "billing@brightstart.org",
            "status": "active",
            "nonprofit_id": nonprofit_id,
        },
    )

    assert vendor_response.status_code == 201

    vendor_id = vendor_response.json()["id"]

    return nonprofit_id, vendor_id