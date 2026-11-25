from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.ai_invoice_analysis import (
    AIInvoiceAnalysis,
)
from app.models.invoice import Invoice
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.dashboard import DashboardResponse


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


@router.get(
    "/summary",
    response_model=DashboardResponse,
)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    invoice_conditions = [
        Invoice.nonprofit_id
        == current_user.nonprofit_id
    ]

    if current_user.role == "vendor":
        if current_user.vendor_id is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Vendor account is not linked "
                    "to a vendor"
                ),
            )

        invoice_conditions.append(
            Invoice.vendor_id
            == current_user.vendor_id
        )

    # ----------------------------------------
    # INVOICE SUMMARY
    # ----------------------------------------

    total_invoices = db.scalar(
        select(
            func.count(Invoice.id)
        ).where(
            *invoice_conditions
        )
    ) or 0

    invoice_status_rows = db.execute(
        select(
            Invoice.status,
            func.count(Invoice.id),
        )
        .where(
            *invoice_conditions
        )
        .group_by(
            Invoice.status
        )
    ).all()

    invoice_status_counts = {
        "submitted": 0,
        "under_review": 0,
        "needs_documents": 0,
        "approved": 0,
        "rejected": 0,
    }

    for (
        invoice_status,
        count,
    ) in invoice_status_rows:
        invoice_status_counts[
            invoice_status
        ] = count

    # ----------------------------------------
    # PAYMENT SUMMARY
    # ----------------------------------------

    payment_query = (
        select(
            Payment.status,
            func.count(Payment.id),
        )
        .join(
            Invoice,
            Payment.invoice_id
            == Invoice.id,
        )
        .where(
            *invoice_conditions
        )
        .group_by(
            Payment.status
        )
    )

    payment_status_rows = db.execute(
        payment_query
    ).all()

    payment_status_counts = {
        "scheduled": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0,
    }

    for (
        payment_status,
        count,
    ) in payment_status_rows:
        payment_status_counts[
            payment_status
        ] = count

    total_payments = sum(
        payment_status_counts.values()
    )

    completed_payment_total = db.scalar(
        select(
            func.coalesce(
                func.sum(Payment.amount),
                Decimal("0.00"),
            )
        )
        .join(
            Invoice,
            Payment.invoice_id
            == Invoice.id,
        )
        .where(
            *invoice_conditions,
            Payment.status == "completed",
        )
    )

    # ----------------------------------------
    # NOTIFICATIONS
    # ----------------------------------------

    unread_notifications = db.scalar(
        select(
            func.count(Notification.id)
        )
        .where(
            Notification.recipient_user_id
            == current_user.id,
            Notification.is_read.is_(
                False
            ),
        )
    ) or 0

    # ----------------------------------------
    # RECENT INVOICES
    # ----------------------------------------

    recent_invoices = db.scalars(
        select(
            Invoice
        )
        .where(
            *invoice_conditions
        )
        .order_by(
            Invoice.id.desc()
        )
        .limit(5)
    ).all()

    # ----------------------------------------
    # AI / AGENTIC ANALYSIS
    # ----------------------------------------

    ai_analysis_rows = db.execute(
        select(
            AIInvoiceAnalysis,
            Invoice,
            Vendor,
        )
        .join(
            Invoice,
            AIInvoiceAnalysis.invoice_id
            == Invoice.id,
        )
        .join(
            Vendor,
            Invoice.vendor_id
            == Vendor.id,
        )
        .where(
            *invoice_conditions
        )
    ).all()

    recommendation_counts = {
        "low_risk": 0,
        "needs_review": 0,
        "needs_documents": 0,
        "high_attention": 0,
    }

    duplicate_risks = 0
    high_attention_risks = 0
    policy_grounded_reviews = 0
    completeness_total = 0

    priority_invoices = []

    for (
        analysis,
        invoice,
        vendor,
    ) in ai_analysis_rows:
        completeness_total += int(
            analysis.completeness_score
            or 0
        )

        if analysis.duplicate_risk:
            duplicate_risks += 1

        if (
            analysis.risk_level
            == "high_attention"
        ):
            high_attention_risks += 1

        extracted_data = (
            analysis.extracted_data
            or {}
        )

        if not isinstance(
            extracted_data,
            dict,
        ):
            extracted_data = {}

        agent_data = (
            extracted_data.get(
                "agent"
            )
            or {}
        )

        recommendation = None

        if isinstance(
            agent_data,
            dict,
        ):
            recommendation = (
                agent_data.get(
                    "recommendation"
                )
            )

        # Support analyses created before
        # the LangGraph agent was added.
        if (
            recommendation
            not in recommendation_counts
        ):
            if analysis.missing_fields:
                recommendation = (
                    "needs_documents"
                )

            elif (
                analysis.duplicate_risk
                or analysis.risk_level
                == "high_attention"
            ):
                recommendation = (
                    "high_attention"
                )

            elif (
                analysis.risk_level
                == "needs_review"
            ):
                recommendation = (
                    "needs_review"
                )

            else:
                recommendation = (
                    "low_risk"
                )

        recommendation_counts[
            recommendation
        ] += 1

        policy_evidence = (
            extracted_data.get(
                "policy_evidence"
            )
            or []
        )

        if policy_evidence:
            policy_grounded_reviews += 1

        priority_invoices.append(
            {
                "invoice_id":
                    invoice.id,

                "invoice_number":
                    invoice.invoice_number,

                "vendor_id":
                    vendor.id,

                "vendor_name":
                    vendor.name,

                "total_amount":
                    invoice.total_amount,

                "currency":
                    invoice.currency,

                "invoice_status":
                    invoice.status,

                "completeness_score":
                    float(
                        analysis
                        .completeness_score
                        or 0
                    ),

                "risk_level":
                    analysis.risk_level,

                "duplicate_risk":
                    analysis.duplicate_risk,

                "recommendation":
                    recommendation,

                "analysis_updated_at":
                    analysis.updated_at,
            }
        )

    analyzed_invoices = len(
        ai_analysis_rows
    )

    if analyzed_invoices:
        average_completeness_score = round(
            completeness_total
            / analyzed_invoices,
            1,
        )
    else:
        average_completeness_score = 0.0

    # ----------------------------------------
    # AI PRIORITY ORDER
    # ----------------------------------------

    recommendation_priority = {
        "high_attention": 0,
        "needs_documents": 1,
        "needs_review": 2,
        "low_risk": 3,
    }

    # Recent analysis first within
    # the same recommendation category.
    priority_invoices.sort(
        key=lambda item:
            item["analysis_updated_at"],
        reverse=True,
    )

    priority_invoices.sort(
        key=lambda item:
            recommendation_priority.get(
                item["recommendation"],
                99,
            )
    )

    # Dashboard should remain concise.
    priority_invoices = (
        priority_invoices[:10]
    )

    ai_review_summary = {
        "analyzed_invoices":
            analyzed_invoices,

        "recommendation_counts":
            recommendation_counts,

        "duplicate_risks":
            duplicate_risks,

        "high_attention_risks":
            high_attention_risks,

        "average_completeness_score":
            average_completeness_score,

        "policy_grounded_reviews":
            policy_grounded_reviews,

        "priority_invoices":
            priority_invoices,
    }

    # ----------------------------------------
    # RESPONSE
    # ----------------------------------------

    return {
        "total_invoices":
            total_invoices,

        "invoice_status_counts":
            invoice_status_counts,

        "total_payments":
            total_payments,

        "payment_status_counts":
            payment_status_counts,

        "completed_payment_total":
            completed_payment_total
            or Decimal("0.00"),

        "unread_notifications":
            unread_notifications,

        "recent_invoices":
            recent_invoices,

        "ai_review_summary":
            ai_review_summary,
    }