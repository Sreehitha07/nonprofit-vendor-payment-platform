from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.services.policy_rag import (
    retrieve_policy_chunks,
)


def build_invoice_policy_query(
    invoice: Invoice,
    analysis_result: dict,
) -> str:
    """
    Build a semantic search query from the
    invoice and its deterministic risk analysis.
    """

    query_parts = [
        (
            "Find nonprofit vendor payment policies "
            "relevant to reviewing this invoice."
        ),
        (
            f"Invoice amount: "
            f"{invoice.total_amount} "
            f"{invoice.currency}."
        ),
        (
            f"Invoice status: "
            f"{invoice.status}."
        ),
    ]

    if analysis_result.get(
        "duplicate_risk"
    ):
        query_parts.append(
            "The invoice may be a duplicate. "
            "Find policies about duplicate invoices, "
            "manual review, and duplicate payment prevention."
        )

    missing_fields = (
        analysis_result.get(
            "missing_fields"
        )
        or []
    )

    if missing_fields:
        query_parts.append(
            "The invoice is missing required information: "
            + ", ".join(
                missing_fields
            )
            + ". Find policies about invoice completeness "
            "and required documentation."
        )

    risk_level = (
        analysis_result.get(
            "risk_level"
        )
    )

    if risk_level:
        query_parts.append(
            f"Current invoice risk level: "
            f"{risk_level}."
        )

    query_parts.append(
        "Also retrieve policies covering manager approval, "
        "supporting documentation, and payment processing "
        "when relevant."
    )

    return " ".join(
        query_parts
    )


def retrieve_invoice_policy_evidence(
    db: Session,
    nonprofit_id: int,
    invoice: Invoice,
    analysis_result: dict,
    limit: int = 5,
) -> list[dict]:
    """
    Retrieve policy passages relevant to
    the current invoice analysis.
    """

    query = build_invoice_policy_query(
        invoice=invoice,
        analysis_result=analysis_result,
    )

    results = retrieve_policy_chunks(
        db=db,
        nonprofit_id=nonprofit_id,
        query=query,
        limit=limit,
    )

    return results