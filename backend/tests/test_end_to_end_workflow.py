from decimal import Decimal


def create_vendor_user(
    client,
    manager_account,
    vendor_id,
):
    register_response = client.post(
        "/api/auth/register",
        headers=manager_account["headers"],
        json={
            "nonprofit_id":
                manager_account["nonprofit_id"],
            "vendor_id":
                vendor_id,
            "full_name":
                "E2E Vendor User",
            "email":
                "e2e-vendor@test.org",
            "password":
                "VendorPass123!",
            "role":
                "vendor",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/token",
        data={
            "username":
                "e2e-vendor@test.org",
            "password":
                "VendorPass123!",
        },
    )

    assert login_response.status_code == 200

    return {
        "Authorization":
            f"Bearer {login_response.json()['access_token']}"
    }


def test_complete_invoice_to_payment_workflow(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    (
        nonprofit_id,
        vendor_id,
        manager_headers,
    ) = nonprofit_and_vendor

    # ---------------------------------------------------------
    # 1. CREATE VENDOR USER
    # ---------------------------------------------------------

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    # ---------------------------------------------------------
    # 2. CREATE INVOICE
    # ---------------------------------------------------------

    create_response = client.post(
        "/api/invoices",
        headers=manager_headers,
        json={
            "nonprofit_id":
                nonprofit_id,
            "vendor_id":
                vendor_id,
            "invoice_number":
                "E2E-DAY21-001",
            "invoice_date":
                "2026-11-25",
            "due_date":
                "2026-12-25",
            "currency":
                "USD",
            "line_items": [
                {
                    "description":
                        "Community outreach services",
                    "quantity":
                        2,
                    "unit_price":
                        400,
                    "category":
                        "Services",
                },
                {
                    "description":
                        "Program materials",
                    "quantity":
                        1,
                    "unit_price":
                        200,
                    "category":
                        "Materials",
                },
            ],
        },
    )

    assert create_response.status_code == 201

    invoice = create_response.json()

    invoice_id = invoice["id"]

    assert invoice["status"] == "submitted"

    assert (
        Decimal(
            str(invoice["total_amount"])
        )
        == Decimal("1000.00")
    )

    # ---------------------------------------------------------
    # 3. MANAGER STARTS REVIEW
    # ---------------------------------------------------------

    start_review = client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=manager_headers,
        json={
            "comments":
                "Beginning end-to-end invoice review."
        },
    )

    assert start_review.status_code == 201

    assert (
        start_review.json()["new_status"]
        == "under_review"
    )

    # ---------------------------------------------------------
    # 4. MANAGER REQUESTS DOCUMENTS
    # ---------------------------------------------------------

    request_documents = client.post(
        f"/api/invoices/{invoice_id}/review/decision",
        headers=manager_headers,
        json={
            "decision":
                "needs_documents",
            "comments":
                "Please upload the supporting purchase order.",
        },
    )

    assert request_documents.status_code == 201

    assert (
        request_documents.json()["new_status"]
        == "needs_documents"
    )

    # ---------------------------------------------------------
    # 5. VENDOR UPLOADS REQUESTED DOCUMENT
    # ---------------------------------------------------------

    upload_response = client.post(
        f"/api/invoices/{invoice_id}/documents",
        headers=vendor_headers,
        data={
            "document_type":
                "purchase_order",
        },
        files={
            "file": (
                "e2e-purchase-order.pdf",
                (
                    b"%PDF-1.4\n"
                    b"E2E supporting purchase order\n"
                ),
                "application/pdf",
            ),
        },
    )

    assert upload_response.status_code == 201

    uploaded_document = (
        upload_response.json()
    )

    assert (
        uploaded_document["document_type"]
        == "purchase_order"
    )

    # ---------------------------------------------------------
    # 6. VENDOR RESUBMITS INVOICE
    # ---------------------------------------------------------

    resubmit_response = client.post(
        f"/api/invoices/{invoice_id}/resubmit",
        headers=vendor_headers,
        json={
            "comments":
                "Requested purchase order uploaded.",
        },
    )

    assert resubmit_response.status_code == 201

    assert (
        resubmit_response.json()["previous_status"]
        == "needs_documents"
    )

    assert (
        resubmit_response.json()["new_status"]
        == "submitted"
    )

    # ---------------------------------------------------------
    # 7. MANAGER STARTS SECOND REVIEW
    # ---------------------------------------------------------

    second_review = client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=manager_headers,
        json={
            "comments":
                "Reviewing resubmitted invoice.",
        },
    )

    assert second_review.status_code == 201

    assert (
        second_review.json()["new_status"]
        == "under_review"
    )

    # ---------------------------------------------------------
    # 8. MANAGER APPROVES INVOICE
    # ---------------------------------------------------------

    approval_response = client.post(
        f"/api/invoices/{invoice_id}/review/decision",
        headers=manager_headers,
        json={
            "decision":
                "approved",
            "comments":
                "Supporting documentation verified.",
        },
    )

    assert approval_response.status_code == 201

    assert (
        approval_response.json()["new_status"]
        == "approved"
    )

    # ---------------------------------------------------------
    # 9. SCHEDULE PAYMENT
    # ---------------------------------------------------------

    payment_response = client.post(
        f"/api/invoices/{invoice_id}/payments",
        headers=manager_headers,
    )

    assert payment_response.status_code == 201

    payment = payment_response.json()

    payment_id = payment["id"]

    assert payment["invoice_id"] == invoice_id

    assert payment["status"] == "scheduled"

    assert payment["payment_method"] == "sandbox"

    assert (
        Decimal(
            str(payment["amount"])
        )
        == Decimal("1000.00")
    )

    # ---------------------------------------------------------
    # 10. START PAYMENT PROCESSING
    # ---------------------------------------------------------

    processing_response = client.post(
        f"/api/payments/{payment_id}/start",
        headers=manager_headers,
    )

    assert processing_response.status_code == 200

    assert (
        processing_response.json()["status"]
        == "processing"
    )

    # ---------------------------------------------------------
    # 11. COMPLETE PAYMENT
    # ---------------------------------------------------------

    completed_response = client.post(
        f"/api/payments/{payment_id}/complete",
        headers=manager_headers,
    )

    assert completed_response.status_code == 200

    completed_payment = (
        completed_response.json()
    )

    assert (
        completed_payment["status"]
        == "completed"
    )

    assert (
        completed_payment["completed_at"]
        is not None
    )

    assert (
        completed_payment[
            "transaction_reference"
        ]
        is not None
    )

    assert (
        completed_payment[
            "transaction_reference"
        ].startswith("TXN-")
    )

    # ---------------------------------------------------------
    # 12. VERIFY PAYMENT AUDIT TRAIL
    # ---------------------------------------------------------

    audit_response = client.get(
        (
            "/api/audit-logs"
            f"?entity_type=payment"
            f"&entity_id={payment_id}"
        ),
        headers=manager_headers,
    )

    assert audit_response.status_code == 200

    audit_logs = audit_response.json()

    assert len(audit_logs) == 3

    payment_actions = {
        item["action"]
        for item in audit_logs
    }

    assert payment_actions == {
        "payment_scheduled",
        "payment_processing_started",
        "payment_completed",
    }

    # ---------------------------------------------------------
    # 13. VERIFY REVIEW HISTORY
    # ---------------------------------------------------------

    review_history_response = client.get(
        f"/api/invoices/{invoice_id}/reviews",
        headers=manager_headers,
    )

    assert (
        review_history_response.status_code
        == 200
    )

    review_history = (
        review_history_response.json()
    )

    review_actions = [
        review["action"]
        for review in review_history
    ]

    assert review_actions.count("started_review") == 2

    assert (
        "requested_documents"
        in review_actions
    )

    assert "resubmitted" in review_actions

    assert "approved" in review_actions

    # ---------------------------------------------------------
    # 14. VERIFY VENDOR CAN VIEW PAYMENT
    # ---------------------------------------------------------

    vendor_payment_response = client.get(
        f"/api/payments/{payment_id}",
        headers=vendor_headers,
    )

    assert (
        vendor_payment_response.status_code
        == 200
    )

    vendor_payment = (
        vendor_payment_response.json()
    )

    assert vendor_payment["id"] == payment_id

    assert (
        vendor_payment["status"]
        == "completed"
    )

    # ---------------------------------------------------------
    # 15. VERIFY VENDOR CANNOT PROCESS PAYMENT
    # ---------------------------------------------------------

    vendor_process_attempt = client.post(
        f"/api/payments/{payment_id}/start",
        headers=vendor_headers,
    )

    assert (
        vendor_process_attempt.status_code
        == 403
    )

    # ---------------------------------------------------------
    # 16. VERIFY DASHBOARD PAYMENT SUMMARY
    # ---------------------------------------------------------

    dashboard_response = client.get(
        "/api/dashboard/summary",
        headers=manager_headers,
    )

    assert dashboard_response.status_code == 200

    dashboard = dashboard_response.json()

    assert dashboard["total_invoices"] == 1

    assert dashboard["total_payments"] == 1

    assert (
        dashboard["payment_status_counts"]
        ["completed"]
        == 1
    )

    assert (
        Decimal(
            str(
                dashboard[
                    "completed_payment_total"
                ]
            )
        )
        == Decimal("1000.00")
    )

    # ---------------------------------------------------------
    # 17. VERIFY VENDOR RECEIVED WORKFLOW NOTIFICATIONS
    # ---------------------------------------------------------

    notification_response = client.get(
        "/api/notifications",
        headers=vendor_headers,
    )

    assert notification_response.status_code == 200

    notifications = (
        notification_response.json()
    )

    notification_types = {
        notification[
            "notification_type"
        ]
        for notification in notifications
    }

    assert (
        "invoice_under_review"
        in notification_types
    )

    assert (
        "payment_scheduled"
        in notification_types
    )

    assert (
        "payment_processing"
        in notification_types
    )

    assert (
        "payment_completed"
        in notification_types
    )