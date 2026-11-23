from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.invoice import Invoice
from app.models.invoice_line_item import (
    InvoiceLineItem,
)


def analyze_invoice_rules(
    db: Session,
    invoice: Invoice,
) -> dict:
    missing_fields: list[str] = []

    if not invoice.invoice_number:
        missing_fields.append(
            "invoice_number"
        )

    if not invoice.invoice_date:
        missing_fields.append(
            "invoice_date"
        )

    if not invoice.due_date:
        missing_fields.append(
            "due_date"
        )

    if not invoice.currency:
        missing_fields.append(
            "currency"
        )

    if (
        invoice.total_amount is None
        or invoice.total_amount
        <= Decimal("0.00")
    ):
        missing_fields.append(
            "total_amount"
        )

    line_item_count = db.scalar(
        select(
            func.count(
                InvoiceLineItem.id
            )
        ).where(
            InvoiceLineItem.invoice_id
            == invoice.id
        )
    )

    if not line_item_count:
        missing_fields.append(
            "line_items"
        )

    document_count = db.scalar(
        select(
            func.count(Document.id)
        ).where(
            Document.invoice_id
            == invoice.id
        )
    )

    if not document_count:
        missing_fields.append(
            "supporting_document"
        )

    total_checks = 7

    passed_checks = (
        total_checks -
        len(missing_fields)
    )

    completeness_score = round(
        (
            passed_checks
            / total_checks
        )
        * 100,
        2,
    )

    date_start = (
        invoice.invoice_date
        - timedelta(days=30)
    )

    date_end = (
        invoice.invoice_date
        + timedelta(days=30)
    )

    possible_duplicate = db.scalar(
        select(Invoice)
        .where(
            Invoice.id != invoice.id,
            Invoice.vendor_id
            == invoice.vendor_id,
            Invoice.total_amount
            == invoice.total_amount,
            Invoice.invoice_date
            >= date_start,
            Invoice.invoice_date
            <= date_end,
        )
        .order_by(
            Invoice.invoice_date.desc(),
            Invoice.id.desc(),
        )
        .limit(1)
    )

    duplicate_risk = (
        possible_duplicate
        is not None
    )

    risk_reasons: list[str] = []

    if duplicate_risk:
        risk_reasons.append(
            "Possible duplicate invoice: "
            "same vendor and amount found "
            "within a 30-day window."
        )

    if not document_count:
        risk_reasons.append(
            "No supporting document "
            "has been uploaded."
        )

    if missing_fields:
        risk_reasons.append(
            "Invoice is missing information "
            "required for complete review."
        )

    if duplicate_risk:
        risk_level = "high_attention"

    elif missing_fields:
        risk_level = "needs_review"

    else:
        risk_level = "low_risk"

    extracted_data = {
        "invoice_number":
            invoice.invoice_number,

        "invoice_date":
            invoice.invoice_date.isoformat()
            if invoice.invoice_date
            else None,

        "due_date":
            invoice.due_date.isoformat()
            if invoice.due_date
            else None,

        "vendor_id":
            invoice.vendor_id,

        "currency":
            invoice.currency,

        "total_amount":
            str(invoice.total_amount),

        "line_item_count":
            int(line_item_count or 0),

        "document_count":
            int(document_count or 0),

        "source":
            "system_invoice_record",
    }

    return {
        "completeness_score":
            completeness_score,

        "missing_fields":
            missing_fields,

        "duplicate_risk":
            duplicate_risk,

        "possible_duplicate_invoice_id":
            (
                possible_duplicate.id
                if possible_duplicate
                else None
            ),

        "risk_level":
            risk_level,

        "risk_reasons":
            risk_reasons,

        "extracted_data":
            extracted_data,
    }

def compare_extracted_invoice(
    invoice: Invoice,
    extracted,
) -> list[str]:
    mismatches: list[str] = []

    if (
        extracted.invoice_number
        and extracted.invoice_number.strip()
        != invoice.invoice_number.strip()
    ):
        mismatches.append(
            "Invoice number in the uploaded "
            "document does not match the "
            "submitted invoice record."
        )

    if (
        extracted.currency
        and extracted.currency.upper()
        != invoice.currency.upper()
    ):
        mismatches.append(
            "Currency in the uploaded "
            "document does not match the "
            "submitted invoice record."
        )

    if (
        extracted.total_amount
        is not None
    ):
        extracted_total = Decimal(
            str(
                extracted.total_amount
            )
        )

        if (
            abs(
                extracted_total
                - invoice.total_amount
            )
            > Decimal("0.01")
        ):
            mismatches.append(
                "Total amount in the uploaded "
                "document does not match the "
                "submitted invoice total."
            )

    if (
        extracted.invoice_date
        and str(invoice.invoice_date)
        != extracted.invoice_date
    ):
        mismatches.append(
            "Invoice date in the uploaded "
            "document does not match the "
            "submitted invoice record."
        )

    return mismatches