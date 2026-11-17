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
from app.models.invoice import Invoice
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.user import User
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
    current_user: User = Depends(get_current_user),
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

    total_invoices = db.scalar(
        select(func.count(Invoice.id))
        .where(*invoice_conditions)
    ) or 0

    invoice_status_rows = db.execute(
        select(
            Invoice.status,
            func.count(Invoice.id),
        )
        .where(*invoice_conditions)
        .group_by(Invoice.status)
    ).all()

    invoice_status_counts = {
        "submitted": 0,
        "under_review": 0,
        "needs_documents": 0,
        "approved": 0,
        "rejected": 0,
    }

    for invoice_status, count in invoice_status_rows:
        invoice_status_counts[
            invoice_status
        ] = count

    payment_query = (
        select(
            Payment.status,
            func.count(Payment.id),
        )
        .join(
            Invoice,
            Payment.invoice_id == Invoice.id,
        )
        .where(*invoice_conditions)
        .group_by(Payment.status)
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

    for payment_status, count in payment_status_rows:
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
            Payment.invoice_id == Invoice.id,
        )
        .where(
            *invoice_conditions,
            Payment.status == "completed",
        )
    )

    unread_notifications = db.scalar(
        select(
            func.count(Notification.id)
        )
        .where(
            Notification.recipient_user_id
            == current_user.id,
            Notification.is_read.is_(False),
        )
    ) or 0

    recent_invoices = db.scalars(
        select(Invoice)
        .where(*invoice_conditions)
        .order_by(Invoice.id.desc())
        .limit(5)
    ).all()

    return {
        "total_invoices": total_invoices,
        "invoice_status_counts":
            invoice_status_counts,
        "total_payments": total_payments,
        "payment_status_counts":
            payment_status_counts,
        "completed_payment_total":
            completed_payment_total
            or Decimal("0.00"),
        "unread_notifications":
            unread_notifications,
        "recent_invoices": recent_invoices,
    }