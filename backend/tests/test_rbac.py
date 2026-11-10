from app.models.nonprofit import Nonprofit
from app.models.vendor import Vendor
from tests.conftest import TestingSessionLocal


def create_vendor_user(
    client,
    manager_account,
    vendor_id: int,
):
    response = client.post(
        "/api/auth/register",
        headers=manager_account["headers"],
        json={
            "nonprofit_id": manager_account["nonprofit_id"],
            "vendor_id": vendor_id,
            "full_name": "Vendor User",
            "email": "vendoruser@test.org",
            "password": "VendorPass123!",
            "role": "vendor",
        },
    )

    assert response.status_code == 201

    login_response = client.post(
        "/api/auth/token",
        data={
            "username": "vendoruser@test.org",
            "password": "VendorPass123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def create_second_vendor(
    client,
    manager_account,
):
    response = client.post(
        "/api/vendors",
        headers=manager_account["headers"],
        json={
            "name": "Second Vendor",
            "contact_name": "Second Contact",
            "email": "secondvendor@test.org",
            "status": "active",
            "nonprofit_id": manager_account["nonprofit_id"],
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def test_vendor_only_lists_own_vendor(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    _, vendor_id, _ = nonprofit_and_vendor

    create_second_vendor(
        client,
        manager_account,
    )

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    response = client.get(
        "/api/vendors",
        headers=vendor_headers,
    )

    assert response.status_code == 200

    vendors = response.json()

    assert len(vendors) == 1
    assert vendors[0]["id"] == vendor_id


def test_vendor_cannot_update_vendor_record(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    _, vendor_id, _ = nonprofit_and_vendor

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    response = client.patch(
        f"/api/vendors/{vendor_id}",
        headers=vendor_headers,
        json={
            "status": "approved"
        },
    )

    assert response.status_code == 403


def test_vendor_cannot_view_other_vendor_invoice(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    second_vendor_id = create_second_vendor(
        client,
        manager_account,
    )

    invoice_response = client.post(
        "/api/invoices",
        headers=manager_headers,
        json={
            "nonprofit_id": nonprofit_id,
            "vendor_id": second_vendor_id,
            "invoice_number": "OTHER-VENDOR-001",
            "invoice_date": "2026-10-01",
            "due_date": "2026-10-31",
            "currency": "USD",
            "line_items": [
                {
                    "description": "Other vendor service",
                    "quantity": 1,
                    "unit_price": 500,
                    "category": "Services",
                }
            ],
        },
    )

    assert invoice_response.status_code == 201

    invoice_id = invoice_response.json()["id"]

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    response = client.get(
        f"/api/invoices/{invoice_id}",
        headers=vendor_headers,
    )

    assert response.status_code == 403


def test_manager_cannot_access_other_nonprofit_vendor(
    client,
    manager_account,
):
    db = TestingSessionLocal()

    second_nonprofit = Nonprofit(
        name="Second Nonprofit",
        registration_number="SECOND-NP-001",
        email="second@test.org",
    )

    db.add(second_nonprofit)
    db.flush()

    second_vendor = Vendor(
        nonprofit_id=second_nonprofit.id,
        name="Outside Vendor",
        contact_name="Outside Contact",
        email="outside@test.org",
        status="active",
    )

    db.add(second_vendor)
    db.commit()

    second_vendor_id = second_vendor.id

    db.close()

    response = client.get(
        f"/api/vendors/{second_vendor_id}",
        headers=manager_account["headers"],
    )

    assert response.status_code == 403