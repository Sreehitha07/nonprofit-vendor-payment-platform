import pytest

import app.routes.documents as documents_route


@pytest.fixture(autouse=True)
def temporary_upload_directory(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        documents_route,
        "UPLOAD_DIR",
        tmp_path,
    )

    return tmp_path


def create_invoice(
    client,
    nonprofit_id,
    vendor_id,
    headers,
    invoice_number="DOC-TEST-001",
):
    response = client.post(
        "/api/invoices",
        headers=headers,
        json={
            "nonprofit_id": nonprofit_id,
            "vendor_id": vendor_id,
            "invoice_number": invoice_number,
            "invoice_date": "2026-11-01",
            "due_date": "2026-12-01",
            "currency": "USD",
            "line_items": [
                {
                    "description": "Testing service",
                    "quantity": 1,
                    "unit_price": 500,
                    "category": "Services",
                }
            ],
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def upload_pdf(
    client,
    invoice_id,
    headers,
):
    return client.post(
        f"/api/invoices/{invoice_id}/documents",
        headers=headers,
        data={
            "document_type": "invoice",
        },
        files={
            "file": (
                "sample-invoice.pdf",
                b"%PDF-1.4 test invoice content",
                "application/pdf",
            )
        },
    )


def test_upload_document(
    client,
    nonprofit_and_vendor,
    temporary_upload_directory,
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

    response = upload_pdf(
        client,
        invoice_id,
        headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["invoice_id"] == invoice_id
    assert (
        data["original_filename"]
        == "sample-invoice.pdf"
    )
    assert data["document_type"] == "invoice"
    assert data["content_type"] == "application/pdf"
    assert data["file_size"] > 0
    assert data["verification_status"] == "pending"

    stored_files = list(
        temporary_upload_directory.iterdir()
    )

    assert len(stored_files) == 1

    # Stored file should use a generated name,
    # not the original user-supplied filename.
    assert (
        stored_files[0].name
        != "sample-invoice.pdf"
    )

    assert stored_files[0].suffix == ".pdf"


def test_list_documents(
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

    upload_response = upload_pdf(
        client,
        invoice_id,
        headers,
    )

    assert upload_response.status_code == 201

    response = client.get(
        f"/api/invoices/{invoice_id}/documents",
        headers=headers,
    )

    assert response.status_code == 200

    documents = response.json()

    assert len(documents) == 1

    assert (
        documents[0]["original_filename"]
        == "sample-invoice.pdf"
    )


def test_download_document(
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

    upload_response = upload_pdf(
        client,
        invoice_id,
        headers,
    )

    document_id = upload_response.json()["id"]

    response = client.get(
        f"/api/documents/{document_id}/download",
        headers=headers,
    )

    assert response.status_code == 200

    assert (
        response.headers["content-type"]
        == "application/pdf"
    )

    assert (
        response.content
        == b"%PDF-1.4 test invoice content"
    )


def test_invalid_file_extension_is_rejected(
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
        f"/api/invoices/{invoice_id}/documents",
        headers=headers,
        data={
            "document_type": "invoice",
        },
        files={
            "file": (
                "malware.exe",
                b"not allowed",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 415


def test_mismatched_content_type_is_rejected(
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
        f"/api/invoices/{invoice_id}/documents",
        headers=headers,
        data={
            "document_type": "invoice",
        },
        files={
            "file": (
                "fake.pdf",
                b"fake content",
                "image/png",
            )
        },
    )

    assert response.status_code == 415


def test_empty_file_is_rejected(
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
        f"/api/invoices/{invoice_id}/documents",
        headers=headers,
        data={
            "document_type": "invoice",
        },
        files={
            "file": (
                "empty.pdf",
                b"",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400


def test_oversized_file_is_rejected(
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

    oversized_content = (
        b"x"
        * (documents_route.MAX_FILE_SIZE + 1)
    )

    response = client.post(
        f"/api/invoices/{invoice_id}/documents",
        headers=headers,
        data={
            "document_type": "invoice",
        },
        files={
            "file": (
                "large.pdf",
                oversized_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413


def test_delete_document_removes_record_and_file(
    client,
    nonprofit_and_vendor,
    temporary_upload_directory,
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

    upload_response = upload_pdf(
        client,
        invoice_id,
        headers,
    )

    assert upload_response.status_code == 201

    document_id = upload_response.json()["id"]

    assert len(
        list(
            temporary_upload_directory.iterdir()
        )
    ) == 1

    delete_response = client.delete(
        f"/api/documents/{document_id}",
        headers=headers,
    )

    assert delete_response.status_code == 204

    assert len(
        list(
            temporary_upload_directory.iterdir()
        )
    ) == 0

    response = client.get(
        f"/api/documents/{document_id}/download",
        headers=headers,
    )

    assert response.status_code == 404


def test_vendor_cannot_access_other_vendor_documents(
    client,
    manager_account,
    nonprofit_and_vendor,
):
    nonprofit_id, vendor_id, manager_headers = (
        nonprofit_and_vendor
    )

    second_vendor_response = client.post(
        "/api/vendors",
        headers=manager_headers,
        json={
            "name": "Second Document Vendor",
            "contact_name": "Second Contact",
            "email": "documents2@test.org",
            "status": "active",
            "nonprofit_id": nonprofit_id,
        },
    )

    assert second_vendor_response.status_code == 201

    second_vendor_id = (
        second_vendor_response.json()["id"]
    )

    second_invoice_id = create_invoice(
        client,
        nonprofit_id,
        second_vendor_id,
        manager_headers,
        "DOC-OTHER-001",
    )

    upload_response = upload_pdf(
        client,
        second_invoice_id,
        manager_headers,
    )

    assert upload_response.status_code == 201

    document_id = upload_response.json()["id"]

    register_response = client.post(
        "/api/auth/register",
        headers=manager_headers,
        json={
            "nonprofit_id": nonprofit_id,
            "vendor_id": vendor_id,
            "full_name": "Restricted Vendor User",
            "email": "restrictedvendor@test.org",
            "password": "VendorPass123!",
            "role": "vendor",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/token",
        data={
            "username": "restrictedvendor@test.org",
            "password": "VendorPass123!",
        },
    )

    assert login_response.status_code == 200

    vendor_headers = {
        "Authorization": (
            "Bearer "
            + login_response.json()["access_token"]
        )
    }

    list_response = client.get(
        f"/api/invoices/{second_invoice_id}/documents",
        headers=vendor_headers,
    )

    assert list_response.status_code == 403

    download_response = client.get(
        f"/api/documents/{document_id}/download",
        headers=vendor_headers,
    )

    assert download_response.status_code == 403