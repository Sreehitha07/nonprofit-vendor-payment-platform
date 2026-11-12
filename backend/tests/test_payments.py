from datetime import date
from decimal import Decimal

from app.core.security import hash_password
from app.models.invoice import Invoice
from app.models.nonprofit import Nonprofit
from app.models.payment import Payment
from app.models.user import User
from app.models.vendor import Vendor
from tests.conftest import TestingSessionLocal


def create_invoice(
    client,
    nonprofit_id,
    vendor_id,
    headers,
    invoice_number="PAY-TEST-001",
):
    response = client.post(
        "/api/invoices",
        headers=headers,
        json={
            "nonprofit_id": nonprofit_id,
            "vendor_id": vendor_id,
            "invoice_number": invoice_number,
            "invoice_date": "2026-11-12",
            "due_date": "2026-12-12",
            "currency": "USD",
            "line_items": [
                {
                    "description": "Payment test service",
                    "quantity": 2,
                    "unit_price": 500,
                    "category": "Services",
                }
            ],
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def approve_invoice(
    client,
    invoice_id,
    headers,
):
    start_response = client.post(
        f"/api/invoices/{invoice_id}/review/start",
        headers=headers,
        json={
            "comments": "Starting payment review."
        },
    )

    assert start_response.status_code == 201

    decision_response = client.post(
        f"/api/invoices/{invoice_id}/review/decision",
        headers=headers,
        json={
            "decision": "approved",
            "comments": "Approved for payment.",
        },
    )

    assert decision_response.status_code == 201


def create_approved_invoice(
    client,
    nonprofit_id,
    vendor_id,
    headers,
    invoice_number="PAY-TEST-001",
):
    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
        invoice_number,
    )

    approve_invoice(
        client,
        invoice_id,
        headers,
    )

    return invoice_id


def schedule_payment(
    client,
    invoice_id,
    headers,
):
    response = client.post(
        f"/api/invoices/{invoice_id}/payments",
        headers=headers,
    )

    assert response.status_code == 201

    return response


def create_vendor_user(
    client,
    manager_account,
    vendor_id,
):
    register_response = client.post(
        "/api/auth/register",
        headers=manager_account["headers"],
        json={
            "nonprofit_id": manager_account[
                "nonprofit_id"
            ],
            "vendor_id": vendor_id,
            "full_name": "Payment Vendor",
            "email": "paymentvendor@test.org",
            "password": "VendorPass123!",
            "role": "vendor",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/token",
        data={
            "username": "paymentvendor@test.org",
            "password": "VendorPass123!",
        },
    )

    assert login_response.status_code == 200

    return {
        "Authorization":
            f"Bearer {login_response.json()['access_token']}"
    }


def test_only_approved_invoice_can_be_scheduled(
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

    response = client.post(
        f"/api/invoices/{invoice_id}/payments",
        headers=headers,
    )

    assert response.status_code == 409


def test_payment_uses_invoice_amount(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_approved_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
    )

    response = schedule_payment(
        client,
        invoice_id,
        headers,
    )

    data = response.json()

    assert data["invoice_id"] == invoice_id
    assert Decimal(str(data["amount"])) == Decimal("1000.00")
    assert data["currency"] == "USD"
    assert data["status"] == "scheduled"
    assert data["payment_method"] == "sandbox"


def test_duplicate_payment_is_rejected(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_approved_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
    )

    first = client.post(
        f"/api/invoices/{invoice_id}/payments",
        headers=headers,
    )

    assert first.status_code == 201

    duplicate = client.post(
        f"/api/invoices/{invoice_id}/payments",
        headers=headers,
    )

    assert duplicate.status_code == 409


def test_payment_can_complete_successfully(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_approved_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
    )

    scheduled = schedule_payment(
        client,
        invoice_id,
        headers,
    )

    payment_id = scheduled.json()["id"]

    started = client.post(
        f"/api/payments/{payment_id}/start",
        headers=headers,
    )

    assert started.status_code == 200
    assert started.json()["status"] == "processing"

    completed = client.post(
        f"/api/payments/{payment_id}/complete",
        headers=headers,
    )

    assert completed.status_code == 200

    data = completed.json()

    assert data["status"] == "completed"
    assert data["completed_at"] is not None
    assert data["transaction_reference"] is not None
    assert data["transaction_reference"].startswith("TXN-")


def test_payment_can_fail_with_reason(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_approved_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
        "PAY-FAIL-001",
    )

    scheduled = schedule_payment(
        client,
        invoice_id,
        headers,
    )

    payment_id = scheduled.json()["id"]

    started = client.post(
        f"/api/payments/{payment_id}/start",
        headers=headers,
    )

    assert started.status_code == 200

    failed = client.post(
        f"/api/payments/{payment_id}/fail",
        headers=headers,
        json={
            "reason": "Sandbox bank processing failure."
        },
    )

    assert failed.status_code == 200

    data = failed.json()

    assert data["status"] == "failed"
    assert (
        data["failure_reason"]
        == "Sandbox bank processing failure."
    )


def test_invalid_payment_transition_is_rejected(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_approved_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
    )

    scheduled = schedule_payment(
        client,
        invoice_id,
        headers,
    )

    payment_id = scheduled.json()["id"]

    # Cannot complete before processing has started.
    response = client.post(
        f"/api/payments/{payment_id}/complete",
        headers=headers,
    )

    assert response.status_code == 409


def test_payment_audit_log_records_full_success_path(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_approved_invoice(
        client,
        nonprofit_id,
        vendor_id,
        headers,
    )

    scheduled = schedule_payment(
        client,
        invoice_id,
        headers,
    )

    payment_id = scheduled.json()["id"]

    client.post(
        f"/api/payments/{payment_id}/start",
        headers=headers,
    )

    client.post(
        f"/api/payments/{payment_id}/complete",
        headers=headers,
    )

    response = client.get(
        (
            "/api/audit-logs"
            f"?entity_type=payment&entity_id={payment_id}"
        ),
        headers=headers,
    )

    assert response.status_code == 200

    audit_logs = response.json()

    assert len(audit_logs) == 3

    actions = {
        log["action"]
        for log in audit_logs
    }

    assert actions == {
        "payment_scheduled",
        "payment_processing_started",
        "payment_completed",
    }


def test_vendor_can_view_own_payment_but_cannot_process_it(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_approved_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
    )

    scheduled = schedule_payment(
        client,
        invoice_id,
        manager_headers,
    )

    payment_id = scheduled.json()["id"]

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    view_response = client.get(
        f"/api/payments/{payment_id}",
        headers=vendor_headers,
    )

    assert view_response.status_code == 200
    assert view_response.json()["id"] == payment_id

    process_response = client.post(
        f"/api/payments/{payment_id}/start",
        headers=vendor_headers,
    )

    assert process_response.status_code == 403


def test_vendor_cannot_access_internal_audit_logs(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    invoice_id = create_approved_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
    )

    schedule_payment(
        client,
        invoice_id,
        manager_headers,
    )

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    response = client.get(
        "/api/audit-logs",
        headers=vendor_headers,
    )

    assert response.status_code == 403


def test_cross_tenant_payment_access_is_forbidden(
    client,
    manager_account,
):
    db = TestingSessionLocal()

    second_nonprofit = Nonprofit(
        name="Second Payment Nonprofit",
        registration_number="PAY-NP-002",
        email="paymentsecond@test.org",
    )

    db.add(second_nonprofit)
    db.flush()

    second_vendor = Vendor(
        nonprofit_id=second_nonprofit.id,
        name="Second Payment Vendor",
        contact_name="Second Contact",
        email="secondpaymentvendor@test.org",
        status="active",
    )

    db.add(second_vendor)
    db.flush()

    second_manager = User(
        nonprofit_id=second_nonprofit.id,
        vendor_id=None,
        full_name="Second Payment Manager",
        email="secondpaymentmanager@test.org",
        password_hash=hash_password(
            "SecurePass123!"
        ),
        role="manager",
        is_active=True,
    )

    db.add(second_manager)
    db.flush()

    second_invoice = Invoice(
        nonprofit_id=second_nonprofit.id,
        vendor_id=second_vendor.id,
        invoice_number="CROSS-TENANT-PAY-001",
        invoice_date=date(2026, 11, 12),
        due_date=date(2026, 12, 12),
        currency="USD",
        total_amount=Decimal("500.00"),
        status="approved",
    )

    db.add(second_invoice)
    db.flush()

    second_payment = Payment(
        invoice_id=second_invoice.id,
        created_by_user_id=second_manager.id,
        amount=Decimal("500.00"),
        currency="USD",
        status="scheduled",
        payment_method="sandbox",
    )

    db.add(second_payment)
    db.commit()

    payment_id = second_payment.id

    db.close()

    response = client.get(
        f"/api/payments/{payment_id}",
        headers=manager_account["headers"],
    )

    assert response.status_code == 403