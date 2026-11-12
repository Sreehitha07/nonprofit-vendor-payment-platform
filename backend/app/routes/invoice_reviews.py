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
from app.models.invoice_review import InvoiceReview
from app.models.user import User
from app.schemas.invoice_review import (
    InvoiceDecisionRequest,
    InvoiceResubmitRequest,
    InvoiceReviewResponse,
    InvoiceStartReviewRequest,
)


router = APIRouter(
    prefix="/api/invoices",
    tags=["Invoice Reviews"],
)


def get_authorized_invoice(
    invoice_id: int,
    current_user: User,
    db: Session,
) -> Invoice:
    invoice = db.get(
        Invoice,
        invoice_id,
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    ensure_vendor_access(
        current_user,
        invoice.vendor_id,
        invoice.nonprofit_id,
    )

    return invoice


def create_review_record(
    db: Session,
    invoice: Invoice,
    current_user: User,
    action: str,
    previous_status: str,
    new_status: str,
    comments: str | None,
) -> InvoiceReview:
    review = InvoiceReview(
        invoice_id=invoice.id,
        performed_by_user_id=current_user.id,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        comments=comments,
    )

    db.add(review)

    return review


@router.post(
    "/{invoice_id}/review/start",
    response_model=InvoiceReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_invoice_review(
    invoice_id: int,
    payload: InvoiceStartReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "staff",
            "manager",
            "admin",
        )
    ),
):
    invoice = get_authorized_invoice(
        invoice_id,
        current_user,
        db,
    )

    if invoice.status != "submitted":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only submitted invoices can "
                "be moved to under review"
            ),
        )

    previous_status = invoice.status

    invoice.status = "under_review"

    review = create_review_record(
        db=db,
        invoice=invoice,
        current_user=current_user,
        action="started_review",
        previous_status=previous_status,
        new_status="under_review",
        comments=payload.comments,
    )

    db.commit()
    db.refresh(review)

    return review


@router.post(
    "/{invoice_id}/review/decision",
    response_model=InvoiceReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def make_invoice_decision(
    invoice_id: int,
    payload: InvoiceDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "manager",
            "admin",
        )
    ),
):
    invoice = get_authorized_invoice(
        invoice_id,
        current_user,
        db,
    )

    if invoice.status != "under_review":
        raise HTTPException(
            status_code=409,
            detail=(
                "A decision can only be made "
                "while an invoice is under review"
            ),
        )

    previous_status = invoice.status

    invoice.status = payload.decision

    action_map = {
        "approved": "approved",
        "rejected": "rejected",
        "needs_documents": "requested_documents",
    }

    review = create_review_record(
        db=db,
        invoice=invoice,
        current_user=current_user,
        action=action_map[payload.decision],
        previous_status=previous_status,
        new_status=payload.decision,
        comments=payload.comments,
    )

    db.commit()
    db.refresh(review)

    return review


@router.post(
    "/{invoice_id}/resubmit",
    response_model=InvoiceReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def resubmit_invoice(
    invoice_id: int,
    payload: InvoiceResubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("vendor")
    ),
):
    invoice = get_authorized_invoice(
        invoice_id,
        current_user,
        db,
    )

    if invoice.status != "needs_documents":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only invoices requesting additional "
                "documents can be resubmitted"
            ),
        )

    previous_status = invoice.status

    invoice.status = "submitted"

    review = create_review_record(
        db=db,
        invoice=invoice,
        current_user=current_user,
        action="resubmitted",
        previous_status=previous_status,
        new_status="submitted",
        comments=payload.comments,
    )

    db.commit()
    db.refresh(review)

    return review


@router.get(
    "/{invoice_id}/reviews",
    response_model=list[InvoiceReviewResponse],
)
def list_invoice_reviews(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    invoice = get_authorized_invoice(
        invoice_id,
        current_user,
        db,
    )

    query = (
        select(InvoiceReview)
        .where(
            InvoiceReview.invoice_id
            == invoice.id
        )
        .order_by(
            InvoiceReview.created_at.asc(),
            InvoiceReview.id.asc(),
        )
    )

    return db.scalars(query).all()