from app.services.invoice_agent_graph import (
    run_invoice_agent,
)


def test_agent_recommends_low_risk():
    result = run_invoice_agent(
        invoice_id=101,
        analysis_result={
            "completeness_score": 100,
            "missing_fields": [],
            "duplicate_risk": False,
            "possible_duplicate_invoice_id": None,
            "risk_level": "low_risk",
            "risk_reasons": [],
        },
        policy_evidence=[
            {
                "policy_document_id": 1,
                "chunk_id": 1,
                "content": (
                    "Complete invoices may proceed "
                    "to human review."
                ),
                "distance": 0.20,
            }
        ],
    )

    assert result["recommendation"] == "low_risk"
    assert result["completeness_status"] == "complete"

    assert (
        result["policy_context_available"]
        is True
    )

    assert result["policy_evidence_count"] == 1

    assert (
        result["human_review_required"]
        is True
    )

    assert (
        result["final_decision_allowed"]
        is False
    )


def test_agent_recommends_needs_documents():
    result = run_invoice_agent(
        invoice_id=102,
        analysis_result={
            "completeness_score": 75,
            "missing_fields": [
                "supporting_document",
            ],
            "duplicate_risk": False,
            "possible_duplicate_invoice_id": None,
            "risk_level": "needs_review",
            "risk_reasons": [
                (
                    "Supporting documentation "
                    "is missing."
                )
            ],
        },
        policy_evidence=[],
    )

    assert (
        result["recommendation"]
        == "needs_documents"
    )

    assert (
        result["completeness_status"]
        == "incomplete"
    )

    assert (
        result["policy_context_available"]
        is False
    )

    assert result["policy_evidence_count"] == 0

    assert (
        result["human_review_required"]
        is True
    )

    assert (
        result["final_decision_allowed"]
        is False
    )


def test_agent_recommends_high_attention_for_duplicate():
    result = run_invoice_agent(
        invoice_id=103,
        analysis_result={
            "completeness_score": 100,
            "missing_fields": [],
            "duplicate_risk": True,
            "possible_duplicate_invoice_id": 88,
            "risk_level": "high_attention",
            "risk_reasons": [
                (
                    "Another invoice with a "
                    "similar amount and date exists."
                )
            ],
        },
        policy_evidence=[
            {
                "policy_document_id": 2,
                "chunk_id": 4,
                "content": (
                    "Potential duplicate invoices "
                    "must be reviewed before payment."
                ),
                "distance": 0.15,
            }
        ],
    )

    assert (
        result["recommendation"]
        == "high_attention"
    )

    assert result["duplicate_risk"] is True

    assert (
        result[
            "possible_duplicate_invoice_id"
        ]
        == 88
    )

    assert (
        result["human_review_required"]
        is True
    )

    assert (
        result["final_decision_allowed"]
        is False
    )

    assert any(
        "Recommendation generated: high_attention."
        in step
        for step in result["agent_trace"]
    )
def test_incomplete_invoice_skips_risk_node():
    result = run_invoice_agent(
        invoice_id=201,
        analysis_result={
            "completeness_score": 70,
            "missing_fields": [
                "supporting_document",
            ],
            "duplicate_risk": False,
            "possible_duplicate_invoice_id": None,
            "risk_level": "needs_review",
            "risk_reasons": [],
        },
        policy_evidence=[],
    )

    trace = result["agent_trace"]

    assert result["recommendation"] == "needs_documents"

    assert any(
        "Routing: incomplete invoice"
        in step
        for step in trace
    )

    assert not any(
        step.startswith("Risk check:")
        for step in trace
    )

    assert any(
        "Conditional route selected: needs documents."
        in step
        for step in trace
    )


def test_duplicate_invoice_uses_high_attention_path():
    result = run_invoice_agent(
        invoice_id=202,
        analysis_result={
            "completeness_score": 100,
            "missing_fields": [],
            "duplicate_risk": True,
            "possible_duplicate_invoice_id": 15,
            "risk_level": "high_attention",
            "risk_reasons": [],
        },
        policy_evidence=[
            {
                "policy_document_id": 1,
                "chunk_id": 2,
                "content": (
                    "Duplicate invoices require "
                    "manual verification."
                ),
                "distance": 0.18,
            }
        ],
    )

    trace = result["agent_trace"]

    assert result["recommendation"] == "high_attention"

    assert any(
        step.startswith("Risk check:")
        for step in trace
    )

    assert any(
        "Conditional route selected: high attention."
        in step
        for step in trace
    )

    assert not any(
        "Conditional route selected: needs documents."
        in step
        for step in trace
    )


def test_low_risk_invoice_uses_standard_path():
    result = run_invoice_agent(
        invoice_id=203,
        analysis_result={
            "completeness_score": 100,
            "missing_fields": [],
            "duplicate_risk": False,
            "possible_duplicate_invoice_id": None,
            "risk_level": "low_risk",
            "risk_reasons": [],
        },
        policy_evidence=[
            {
                "policy_document_id": 1,
                "chunk_id": 3,
                "content": (
                    "Complete invoices may move "
                    "to human review."
                ),
                "distance": 0.25,
            }
        ],
    )

    trace = result["agent_trace"]

    assert result["recommendation"] == "low_risk"

    assert any(
        step.startswith("Risk check:")
        for step in trace
    )

    assert any(
        "Conditional route selected: standard review."
        in step
        for step in trace
    )

    assert not any(
        "Conditional route selected: high attention."
        in step
        for step in trace
    )