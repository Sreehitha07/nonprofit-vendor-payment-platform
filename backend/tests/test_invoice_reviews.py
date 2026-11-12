def create_invoice(
    client,
    nonprofit_id,
    vendor_id,
    headers,
    invoice_number="REVIEW-TEST-001",
):
    response = client.post(
        "/api/invoices",
        headers=headers,
        json={
            "nonprofit_id": nonprofit_id,
            "vendor_id": vendor_id,
            "invoice_number": invoice_number,
            "invoice_date": "2026-11-11",
            "due_date": "2026-12-11",
            "currency": "USD",
            "line_items": [
                {
                    "description": "Review workflow service",
                    "quantity": 1,
                    "unit_price": 1000,
                    "category": "Services",
                }
            ],
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def create_staff_user(
    client,
    manager_account,
):
    response = client.post(
        "/api/auth/register",
        headers=manager_account["headers"],
        json={
            "nonprofit_id": manager_account["nonprofit_id"],
            "full_name": "Review Staff",
            "email": "reviewstaff@test.org",
            "password": "StaffPass123!",
            "role": "staff",
        },
    )

    assert response.status_code == 201

    login = client.post(
        "/api/auth/token",
        data={
            "username": "reviewstaff@test.org",
            "password": "StaffPass123!",
        },
    )

    assert login.status_code == 200

    return {
        "Authorization":
            f"Bearer {login.json()['access_token']}"
    }


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
            "full_name": "Review Vendor",
            "email": "reviewvendor@test.org",
            "password": "VendorPass123!",
            "role": "vendor",
        },
    )

    assert response.status_code == 201

    login = client.post(
        "/api/auth/token",
        data={
            "username": "reviewvendor@test.org",
            "password": "VendorPass123!",
        },
    )

    assert login.status_code == 200

    return {
        "Authorization":
            f"Bearer {login.json()['access_token']}"
    }


def test_manager_can_approve_invoice(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
    )

    start_response = client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=headers,
        json={
            "comments": "Starting review."
        },
    )

    assert start_response.status_code == 201
    assert (
        start_response.json()["new_status"]
        == "under_review"
    )

    decision_response = client.post(
        f"/api/invoices/{invoice_id}/review/decision",
        headers=headers,
        json={
            "decision": "approved",
            "comments": "Invoice verified."
        },
    )

    assert decision_response.status_code == 201

    data = decision_response.json()

    assert data["action"] == "approved"
    assert data["previous_status"] == "under_review"
    assert data["new_status"] == "approved"

    invoice_response = client.get(
        f"/api/invoices/{invoice_id}",
        headers=headers,
    )

    assert invoice_response.status_code == 200
    assert invoice_response.json()["status"] == "approved"


def test_manager_can_reject_invoice_with_reason(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
        "REVIEW-TEST-002",
    )

    client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=headers,
        json={},
    )

    response = client.post(
        f"/api/invoices/{invoice_id}/review/decision",
        headers=headers,
        json={
            "decision": "rejected",
            "comments": "Invoice amount could not be verified.",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["action"] == "rejected"
    assert data["new_status"] == "rejected"


def test_rejection_requires_comments(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
        "REVIEW-TEST-003",
    )

    client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=headers,
        json={},
    )

    response = client.post(
        f"/api/invoices/{invoice_id}/review/decision",
        headers=headers,
        json={
            "decision": "rejected",
            "comments": None,
        },
    )

    assert response.status_code == 422


def test_invalid_status_transition_is_rejected(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
        "REVIEW-TEST-004",
    )

    first_response = client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=headers,
        json={},
    )

    assert first_response.status_code == 201

    second_response = client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=headers,
        json={},
    )

    assert second_response.status_code == 409


def test_staff_can_start_review_but_cannot_decide(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
        "REVIEW-TEST-005",
    )

    staff_headers = create_staff_user(
        client,
        manager_account,
    )

    start_response = client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=staff_headers,
        json={
            "comments": "Staff review started."
        },
    )

    assert start_response.status_code == 201

    decision_response = client.post(
        f"/api/invoices/{invoice_id}/review/decision",
        headers=staff_headers,
        json={
            "decision": "approved",
            "comments": "Attempting approval."
        },
    )

    assert decision_response.status_code == 403


def test_vendor_can_resubmit_when_documents_requested(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
        "REVIEW-TEST-006",
    )

    client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=manager_headers,
        json={},
    )

    request_documents = client.post(
        f"/api/invoices/{invoice_id}/review/decision",
        headers=manager_headers,
        json={
            "decision": "needs_documents",
            "comments": "Please upload the purchase order.",
        },
    )

    assert request_documents.status_code == 201

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    response = client.post(
        f"/api/invoices/{invoice_id}/resubmit",
        headers=vendor_headers,
        json={
            "comments":
                "Requested purchase order uploaded."
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["action"] == "resubmitted"
    assert data["previous_status"] == "needs_documents"
    assert data["new_status"] == "submitted"


def test_vendor_cannot_resubmit_normal_submitted_invoice(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
        "REVIEW-TEST-007",
    )

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    response = client.post(
        f"/api/invoices/{invoice_id}/resubmit",
        headers=vendor_headers,
        json={
            "comments": "Trying invalid resubmission."
        },
    )

    assert response.status_code == 409


def test_review_history_records_full_workflow(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
        "REVIEW-TEST-008",
    )

    client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=manager_headers,
        json={
            "comments": "First review."
        },
    )

    client.post(
        f"/api/invoices/{invoice_id}/review/decision",
        headers=manager_headers,
        json={
            "decision": "needs_documents",
            "comments": "Missing purchase order.",
        },
    )

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    client.post(
        f"/api/invoices/{invoice_id}/resubmit",
        headers=vendor_headers,
        json={
            "comments": "Purchase order uploaded."
        },
    )

    response = client.get(
        f"/api/invoices/{invoice_id}/reviews",
        headers=vendor_headers,
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 3

    assert history[0]["action"] == "started_review"
    assert history[0]["previous_status"] == "submitted"
    assert history[0]["new_status"] == "under_review"

    assert history[1]["action"] == "requested_documents"
    assert history[1]["previous_status"] == "under_review"
    assert history[1]["new_status"] == "needs_documents"

    assert history[2]["action"] == "resubmitted"
    assert history[2]["previous_status"] == "needs_documents"
    assert history[2]["new_status"] == "submitted"