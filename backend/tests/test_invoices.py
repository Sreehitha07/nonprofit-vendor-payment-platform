def valid_invoice_payload(
    nonprofit_id: int,
    vendor_id: int,
    invoice_number: str = "INV-TEST-001",
):
    return {
        "nonprofit_id": nonprofit_id,
        "vendor_id": vendor_id,
        "invoice_number": invoice_number,
        "invoice_date": "2026-09-26",
        "due_date": "2026-10-26",
        "currency": "USD",
        "line_items": [
            {
                "description": "Childcare services",
                "quantity": 20,
                "unit_price": 100,
                "category": "Services",
            },
            {
                "description": "Transportation services",
                "quantity": 10,
                "unit_price": 80,
                "category": "Transportation",
            },
            {
                "description": "Educational supplies",
                "quantity": 4,
                "unit_price": 100,
                "category": "Supplies",
            },
        ],
    }


def test_create_invoice_and_calculate_total(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id = nonprofit_and_vendor

    payload = valid_invoice_payload(
        nonprofit_id,
        vendor_id,
    )

    response = client.post(
        "/api/invoices",
        json=payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["invoice_number"] == "INV-TEST-001"
    assert data["total_amount"] == "3200.00"
    assert data["currency"] == "USD"
    assert data["status"] == "submitted"

    assert len(data["line_items"]) == 3

    assert (
        data["line_items"][0]["line_total"]
        == "2000.00"
    )


def test_duplicate_invoice_is_rejected(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id = nonprofit_and_vendor

    payload = valid_invoice_payload(
        nonprofit_id,
        vendor_id,
    )

    first_response = client.post(
        "/api/invoices",
        json=payload,
    )

    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/api/invoices",
        json=payload,
    )

    assert duplicate_response.status_code == 409

    assert duplicate_response.json()["detail"] == (
        "Invoice number already exists for this vendor"
    )


def test_due_date_before_invoice_date_is_rejected(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id = nonprofit_and_vendor

    payload = valid_invoice_payload(
        nonprofit_id,
        vendor_id,
        "INV-TEST-002",
    )

    payload["due_date"] = "2026-09-20"

    response = client.post(
        "/api/invoices",
        json=payload,
    )

    assert response.status_code == 422


def test_negative_quantity_is_rejected(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id = nonprofit_and_vendor

    payload = valid_invoice_payload(
        nonprofit_id,
        vendor_id,
        "INV-TEST-003",
    )

    payload["line_items"][0]["quantity"] = -2

    response = client.post(
        "/api/invoices",
        json=payload,
    )

    assert response.status_code == 422


def test_get_invoice(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id = nonprofit_and_vendor

    payload = valid_invoice_payload(
        nonprofit_id,
        vendor_id,
    )

    created = client.post(
        "/api/invoices",
        json=payload,
    )

    invoice_id = created.json()["id"]

    response = client.get(
        f"/api/invoices/{invoice_id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == invoice_id


def test_filter_invoices_by_vendor(
    client,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id = nonprofit_and_vendor

    client.post(
        "/api/invoices",
        json=valid_invoice_payload(
            nonprofit_id,
            vendor_id,
        ),
    )

    response = client.get(
        f"/api/invoices?vendor_id={vendor_id}"
    )

    assert response.status_code == 200

    invoices = response.json()

    assert len(invoices) == 1
    assert invoices[0]["vendor_id"] == vendor_id