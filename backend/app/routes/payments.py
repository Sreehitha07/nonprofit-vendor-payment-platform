from datetime import datetime, timezone
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import (
    ensure_vendor_access,
    get_current_user,
    require_roles,
)
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import (
    PaymentFailureRequest,
    PaymentResponse,
)
from app.services.audit import create_audit_log


router = APIRouter(
    prefix="/api",
    tags=["Payments"],
)


def get_authorized_payment(
    payment_id: int,
    current_user: User,
    db: Session,
) -> tuple[Payment, Invoice]:
    payment = db.get(
        Payment,
        payment_id,
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    invoice = db.get(
        Invoice,
        payment.invoice_id,
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Associated invoice not found",
        )

    ensure_vendor_access(
        current_user,
        invoice.vendor_id,
        invoice.nonprofit_id,
    )

    return payment, invoice


@router.post(
    "/invoices/{invoice_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def schedule_payment(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "manager",
            "admin",
        )
    ),
):
    invoice = db.get(
        Invoice,
        invoice_id,
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    if invoice.nonprofit_id != current_user.nonprofit_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this nonprofit",
        )

    if invoice.status != "approved":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only approved invoices can "
                "be scheduled for payment"
            ),
        )

    existing_payment = db.scalar(
        select(Payment).where(
            Payment.invoice_id == invoice.id
        )
    )

    if existing_payment:
        raise HTTPException(
            status_code=409,
            detail=(
                "A payment already exists "
                "for this invoice"
            ),
        )

    payment = Payment(
        invoice_id=invoice.id,
        created_by_user_id=current_user.id,
        amount=invoice.total_amount,
        currency=invoice.currency,
        status="scheduled",
        payment_method="sandbox",
    )

    db.add(payment)
    db.flush()

    create_audit_log(
        db=db,
        current_user=current_user,
        nonprofit_id=invoice.nonprofit_id,
        entity_type="payment",
        entity_id=payment.id,
        action="payment_scheduled",
        previous_status=None,
        new_status="scheduled",
        description=(
            f"Payment scheduled for invoice "
            f"{invoice.invoice_number}"
        ),
    )

    db.commit()
    db.refresh(payment)

    return payment


@router.post(
    "/payments/{payment_id}/start",
    response_model=PaymentResponse,
)
def start_payment_processing(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "manager",
            "admin",
        )
    ),
):
    payment, invoice = get_authorized_payment(
        payment_id,
        current_user,
        db,
    )

    if payment.status != "scheduled":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only scheduled payments "
                "can begin processing"
            ),
        )

    previous_status = payment.status

    payment.status = "processing"
    payment.processing_started_at = datetime.now(
        timezone.utc
    )

    create_audit_log(
        db=db,
        current_user=current_user,
        nonprofit_id=invoice.nonprofit_id,
        entity_type="payment",
        entity_id=payment.id,
        action="payment_processing_started",
        previous_status=previous_status,
        new_status="processing",
        description=(
            f"Payment processing started for "
            f"invoice {invoice.invoice_number}"
        ),
    )

    db.commit()
    db.refresh(payment)

    return payment


@router.post(
    "/payments/{payment_id}/complete",
    response_model=PaymentResponse,
)
def complete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "manager",
            "admin",
        )
    ),
):
    payment, invoice = get_authorized_payment(
        payment_id,
        current_user,
        db,
    )

    if payment.status != "processing":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only processing payments "
                "can be completed"
            ),
        )

    previous_status = payment.status

    payment.status = "completed"
    payment.completed_at = datetime.now(
        timezone.utc
    )

    payment.transaction_reference = (
        f"TXN-{uuid4().hex[:16].upper()}"
    )

    create_audit_log(
        db=db,
        current_user=current_user,
        nonprofit_id=invoice.nonprofit_id,
        entity_type="payment",
        entity_id=payment.id,
        action="payment_completed",
        previous_status=previous_status,
        new_status="completed",
        description=(
            f"Payment completed for invoice "
            f"{invoice.invoice_number}. "
            f"Transaction reference: "
            f"{payment.transaction_reference}"
        ),
    )

    db.commit()
    db.refresh(payment)

    return payment


@router.post(
    "/payments/{payment_id}/fail",
    response_model=PaymentResponse,
)
def fail_payment(
    payment_id: int,
    payload: PaymentFailureRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "manager",
            "admin",
        )
    ),
):
    payment, invoice = get_authorized_payment(
        payment_id,
        current_user,
        db,
    )

    if payment.status != "processing":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only processing payments "
                "can be marked as failed"
            ),
        )

    previous_status = payment.status

    payment.status = "failed"
    payment.failure_reason = payload.reason

    create_audit_log(
        db=db,
        current_user=current_user,
        nonprofit_id=invoice.nonprofit_id,
        entity_type="payment",
        entity_id=payment.id,
        action="payment_failed",
        previous_status=previous_status,
        new_status="failed",
        description=payload.reason,
    )

    db.commit()
    db.refresh(payment)

    return payment


@router.get(
    "/payments",
    response_model=list[PaymentResponse],
)
def list_payments(
    payment_status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    query = (
        select(Payment)
        .join(
            Invoice,
            Payment.invoice_id == Invoice.id,
        )
        .where(
            Invoice.nonprofit_id
            == current_user.nonprofit_id
        )
        .order_by(
            Payment.id.desc()
        )
    )

    if current_user.role == "vendor":
        if current_user.vendor_id is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Vendor account is not "
                    "linked to a vendor"
                ),
            )

        query = query.where(
            Invoice.vendor_id
            == current_user.vendor_id
        )

    if payment_status is not None:
        query = query.where(
            Payment.status == payment_status
        )

    return db.scalars(query).all()


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    payment, _ = get_authorized_payment(
        payment_id,
        current_user,
        db,
    )

    return payment