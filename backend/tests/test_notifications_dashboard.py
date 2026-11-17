def create_vendor_user(
    client,
    manager_account,
    vendor_id,
):
    response = client.post(
        "/api/auth/register",
        headers=manager_account["headers"],
        json={
            "nonprofit_id": manager_account["nonprofit_id"],
            "vendor_id": vendor_id,
            "full_name": "Dashboard Vendor",
            "email": "dashboardvendor@test.org",
            "password": "VendorPass123!",
            "role": "vendor",
        },
    )

    assert response.status_code == 201

    login = client.post(
        "/api/auth/token",
        data={
            "username": "dashboardvendor@test.org",
            "password": "VendorPass123!",
        },
    )

    assert login.status_code == 200

    return {
        "Authorization":
            f"Bearer {login.json()['access_token']}"
    }


def create_invoice(
    client,
    nonprofit_id,
    vendor_id,
    headers,
    number="DASH-001",
):
    response = client.post(
        "/api/invoices",
        headers=headers,
        json={
            "nonprofit_id": nonprofit_id,
            "vendor_id": vendor_id,
            "invoice_number": number,
            "invoice_date": "2026-11-16",
            "due_date": "2026-12-16",
            "currency": "USD",
            "line_items": [
                {
                    "description": "Dashboard test service",
                    "quantity": 1,
                    "unit_price": 750,
                    "category": "Services",
                }
            ],
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def test_vendor_receives_review_notification(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
    )

    response = client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=manager_headers,
        json={
            "comments": "Starting notification test."
        },
    )

    assert response.status_code == 201

    notifications = client.get(
        "/api/notifications",
        headers=vendor_headers,
    )

    assert notifications.status_code == 200

    data = notifications.json()

    assert len(data) == 1
    assert (
        data[0]["notification_type"]
        == "invoice_under_review"
    )
    assert data[0]["is_read"] is False


def test_notification_unread_count_and_mark_read(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
    )

    client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=manager_headers,
        json={},
    )

    count = client.get(
        "/api/notifications/unread-count",
        headers=vendor_headers,
    )

    assert count.status_code == 200
    assert count.json()["unread_count"] == 1

    notifications = client.get(
        "/api/notifications",
        headers=vendor_headers,
    ).json()

    notification_id = notifications[0]["id"]

    read_response = client.patch(
        f"/api/notifications/{notification_id}/read",
        headers=vendor_headers,
    )

    assert read_response.status_code == 200
    assert read_response.json()["is_read"] is True
    assert read_response.json()["read_at"] is not None

    count_after = client.get(
        "/api/notifications/unread-count",
        headers=vendor_headers,
    )

    assert count_after.json()["unread_count"] == 0


def test_user_cannot_read_another_users_notification(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
    )

    client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=manager_headers,
        json={},
    )

    notification = client.get(
        "/api/notifications",
        headers=vendor_headers,
    ).json()[0]

    response = client.patch(
        f"/api/notifications/{notification['id']}/read",
        headers=manager_headers,
    )

    assert response.status_code == 403


def test_manager_dashboard_summary(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, headers = (
        nonprofit_and_vendor
    )

    create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
    )

    response = client.get(
        "/api/dashboard/summary",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_invoices"] == 1
    assert (
        data["invoice_status_counts"]["submitted"]
        == 1
    )
    assert data["total_payments"] == 0
    assert data["completed_payment_total"] == "0.00"
    assert len(data["recent_invoices"]) == 1


def test_vendor_dashboard_only_contains_own_data(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
        "OWN-DASH-001",
    )

    second_vendor = client.post(
        "/api/vendors",
        headers=manager_headers,
        json={
            "name": "Other Dashboard Vendor",
            "contact_name": "Other Contact",
            "email": "otherdashboard@test.org",
            "status": "active",
            "nonprofit_id": nonprofit_id,
        },
    )

    assert second_vendor.status_code == 201

    second_vendor_id = second_vendor.json()["id"]

    create_invoice(
        client,
        nonprofit_id,
        second_vendor_id,
        manager_headers,
        "OTHER-DASH-001",
    )

    response = client.get(
        "/api/dashboard/summary",
        headers=vendor_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_invoices"] == 1
    assert len(data["recent_invoices"]) == 1

    assert (
        data["recent_invoices"][0]["vendor_id"]
        == vendor_id
    )