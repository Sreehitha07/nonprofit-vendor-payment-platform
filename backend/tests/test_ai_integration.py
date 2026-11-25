def create_invoice(
    client,
    nonprofit_id,
    vendor_id,
    headers,
    invoice_number,
    amount=500,
):
    response = client.post(
        "/api/invoices",
        headers=headers,
        json={
            "nonprofit_id": nonprofit_id,
            "vendor_id": vendor_id,
            "invoice_number": invoice_number,
            "invoice_date": "2026-11-20",
            "due_date": "2026-12-20",
            "currency": "USD",
            "line_items": [
                {
                    "description":
                        "AI integration test service",
                    "quantity": 1,
                    "unit_price": amount,
                    "category": "Services",
                }
            ],
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def upload_invoice_document(
    client,
    invoice_id,
    headers,
):
    response = client.post(
        f"/api/invoices/{invoice_id}/documents",
        headers=headers,
        data={
            "document_type": "invoice",
        },
        files={
            "file": (
                f"invoice-{invoice_id}.pdf",
                (
                    b"%PDF-1.4\n"
                    b"AI integration test invoice\n"
                ),
                "application/pdf",
            ),
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
            "nonprofit_id":
                manager_account["nonprofit_id"],
            "vendor_id": None,
            "full_name":
                "AI Integration Staff",
            "email":
                "ai-staff@test.org",
            "password":
                "StaffPass123!",
            "role":
                "staff",
        },
    )

    assert response.status_code == 201

    login = client.post(
        "/api/auth/token",
        data={
            "username":
                "ai-staff@test.org",
            "password":
                "StaffPass123!",
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
            "nonprofit_id":
                manager_account["nonprofit_id"],
            "vendor_id":
                vendor_id,
            "full_name":
                "AI Integration Vendor",
            "email":
                "ai-vendor@test.org",
            "password":
                "VendorPass123!",
            "role":
                "vendor",
        },
    )

    assert response.status_code == 201

    login = client.post(
        "/api/auth/token",
        data={
            "username":
                "ai-vendor@test.org",
            "password":
                "VendorPass123!",
        },
    )

    assert login.status_code == 200

    return {
        "Authorization":
            f"Bearer {login.json()['access_token']}"
    }


def create_second_vendor(
    client,
    nonprofit_id,
    manager_headers,
):
    response = client.post(
        "/api/vendors",
        headers=manager_headers,
        json={
            "name":
                "Second AI Test Vendor",
            "contact_name":
                "Second Contact",
            "email":
                "second-ai-vendor@test.org",
            "status":
                "active",
            "nonprofit_id":
                nonprofit_id,
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def disable_policy_rag(
    monkeypatch,
):
    """
    Keep integration tests deterministic.

    RAG itself is tested separately; these tests
    validate the API, agent persistence, RBAC,
    and dashboard integration.
    """

    monkeypatch.setattr(
        (
            "app.routes.ai_analysis."
            "retrieve_invoice_policy_evidence"
        ),
        lambda **kwargs: [],
    )


def run_analysis(
    client,
    invoice_id,
    headers,
):
    return client.post(
        f"/api/ai/invoices/{invoice_id}/analyze",
        headers=headers,
        json={
            "source_document_id": None,
        },
    )


def test_ai_analysis_role_permissions(
    client,
    manager_account,
    nonprofit_and_vendor,
    monkeypatch,
):
    disable_policy_rag(
        monkeypatch
    )

    (
        nonprofit_id,
        vendor_id,
        manager_headers,
    ) = nonprofit_and_vendor

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
        "AI-RBAC-001",
    )

    upload_invoice_document(
        client,
        invoice_id,
        manager_headers,
    )

    # Manager may analyze.
    manager_response = run_analysis(
        client,
        invoice_id,
        manager_headers,
    )

    assert manager_response.status_code == 200

    # Staff may also analyze.
    staff_headers = create_staff_user(
        client,
        manager_account,
    )

    staff_response = run_analysis(
        client,
        invoice_id,
        staff_headers,
    )

    assert staff_response.status_code == 200

    # Vendor must not be allowed
    # to run AI analysis.
    vendor_headers = create_vendor_user(
        client,
        manager_account,
        vendor_id,
    )

    vendor_response = run_analysis(
        client,
        invoice_id,
        vendor_headers,
    )

    assert vendor_response.status_code == 403


def test_ai_analysis_persists_agent_guardrail(
    client,
    nonprofit_and_vendor,
    monkeypatch,
):
    disable_policy_rag(
        monkeypatch
    )

    (
        nonprofit_id,
        vendor_id,
        manager_headers,
    ) = nonprofit_and_vendor

    invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
        "AI-PERSIST-001",
    )

    upload_invoice_document(
        client,
        invoice_id,
        manager_headers,
    )

    response = run_analysis(
        client,
        invoice_id,
        manager_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["invoice_id"]
        == invoice_id
    )

    agent = (
        data["extracted_data"]["agent"]
    )

    assert agent["recommendation"] in {
        "low_risk",
        "needs_review",
        "needs_documents",
        "high_attention",
    }

    assert (
        agent["human_review_required"]
        is True
    )

    assert (
        agent["final_decision_allowed"]
        is False
    )

    assert len(
        agent["agent_trace"]
    ) > 0

    # Verify stored analysis can be
    # retrieved again from the API.
    stored_response = client.get(
        (
            f"/api/ai/invoices/"
            f"{invoice_id}/analysis"
        ),
        headers=manager_headers,
    )

    assert stored_response.status_code == 200

    stored = stored_response.json()

    stored_agent = (
        stored["extracted_data"]["agent"]
    )

    assert (
        stored_agent["recommendation"]
        == agent["recommendation"]
    )

    assert (
        stored_agent["human_review_required"]
        is True
    )

    assert (
        stored_agent["final_decision_allowed"]
        is False
    )


def test_dashboard_prioritizes_high_attention_invoice(
    client,
    nonprofit_and_vendor,
    monkeypatch,
):
    disable_policy_rag(
        monkeypatch
    )

    (
        nonprofit_id,
        vendor_id,
        manager_headers,
    ) = nonprofit_and_vendor

    # Unique invoice -> expected low risk.
    low_risk_invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
        "AI-LOW-001",
        amount=125,
    )

    upload_invoice_document(
        client,
        low_risk_invoice_id,
        manager_headers,
    )

    # Seed invoice for duplicate detection.
    create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
        "AI-DUP-SEED",
        amount=900,
    )

    # Matching amount/date/vendor ->
    # expected duplicate/high attention.
    duplicate_invoice_id = create_invoice(
        client,
        nonprofit_id,
        vendor_id,
        manager_headers,
        "AI-DUP-001",
        amount=900,
    )

    upload_invoice_document(
        client,
        duplicate_invoice_id,
        manager_headers,
    )

    low_response = run_analysis(
        client,
        low_risk_invoice_id,
        manager_headers,
    )

    assert low_response.status_code == 200

    duplicate_response = run_analysis(
        client,
        duplicate_invoice_id,
        manager_headers,
    )

    assert duplicate_response.status_code == 200

    duplicate_agent = (
        duplicate_response
        .json()["extracted_data"]["agent"]
    )

    assert (
        duplicate_agent["recommendation"]
        == "high_attention"
    )

    dashboard_response = client.get(
        "/api/dashboard/summary",
        headers=manager_headers,
    )

    assert dashboard_response.status_code == 200

    queue = (
        dashboard_response
        .json()["ai_review_summary"]
        ["priority_invoices"]
    )

    assert len(queue) == 2

    # High-attention invoice must be
    # above the lower-priority analysis.
    assert (
        queue[0]["invoice_id"]
        == duplicate_invoice_id
    )

    assert (
        queue[0]["recommendation"]
        == "high_attention"
    )

    assert (
        queue[1]["invoice_id"]
        == low_risk_invoice_id
    )

    assert (
        queue[1]["recommendation"]
        == "low_risk"
    )


def test_vendor_dashboard_ai_summary_is_isolated(
    client,
    manager_account,
    nonprofit_and_vendor,
    monkeypatch,
):
    disable_policy_rag(
        monkeypatch
    )

    (
        nonprofit_id,
        first_vendor_id,
        manager_headers,
    ) = nonprofit_and_vendor

    second_vendor_id = create_second_vendor(
        client,
        nonprofit_id,
        manager_headers,
    )

    first_invoice_id = create_invoice(
        client,
        nonprofit_id,
        first_vendor_id,
        manager_headers,
        "AI-VENDOR-OWN",
        amount=310,
    )

    upload_invoice_document(
        client,
        first_invoice_id,
        manager_headers,
    )

    second_invoice_id = create_invoice(
        client,
        nonprofit_id,
        second_vendor_id,
        manager_headers,
        "AI-VENDOR-OTHER",
        amount=875,
    )

    upload_invoice_document(
        client,
        second_invoice_id,
        manager_headers,
    )

    first_analysis = run_analysis(
        client,
        first_invoice_id,
        manager_headers,
    )

    assert first_analysis.status_code == 200

    second_analysis = run_analysis(
        client,
        second_invoice_id,
        manager_headers,
    )

    assert second_analysis.status_code == 200

    vendor_headers = create_vendor_user(
        client,
        manager_account,
        first_vendor_id,
    )

    dashboard_response = client.get(
        "/api/dashboard/summary",
        headers=vendor_headers,
    )

    assert dashboard_response.status_code == 200

    ai_summary = (
        dashboard_response
        .json()["ai_review_summary"]
    )

    # Vendor must see only its own
    # analyzed invoice.
    assert (
        ai_summary["analyzed_invoices"]
        == 1
    )

    assert (
        len(
            ai_summary["priority_invoices"]
        )
        == 1
    )

    assert (
        ai_summary
        ["priority_invoices"][0]
        ["invoice_id"]
        == first_invoice_id
    )

    assert (
        ai_summary
        ["priority_invoices"][0]
        ["vendor_id"]
        == first_vendor_id
    )

    total_recommendations = sum(
        ai_summary[
            "recommendation_counts"
        ].values()
    )

    assert total_recommendations == 1