from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies.auth import (
    ensure_vendor_access,
    get_current_user,
)
from app.models.invoice import Invoice
from app.models.invoice_line_item import InvoiceLineItem
from app.models.nonprofit import Nonprofit
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceResponse,
)


router = APIRouter(
    prefix="/api/invoices",
    tags=["Invoices"],
)


def calculate_money(value: Decimal) -> Decimal:
    return value.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    nonprofit = db.get(
        Nonprofit,
        payload.nonprofit_id,
    )

    if not nonprofit:
        raise HTTPException(
            status_code=404,
            detail="Nonprofit not found",
        )

    if payload.nonprofit_id != current_user.nonprofit_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot submit invoices for another nonprofit",
        )

    vendor = db.get(
        Vendor,
        payload.vendor_id,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    if vendor.nonprofit_id != payload.nonprofit_id:
        raise HTTPException(
            status_code=400,
            detail="Vendor does not belong to this nonprofit",
        )

    if current_user.role == "vendor":
        if current_user.vendor_id != payload.vendor_id:
            raise HTTPException(
                status_code=403,
                detail="You can only submit invoices for your own vendor account",
            )

    existing_invoice = db.scalar(
        select(Invoice).where(
            Invoice.vendor_id == payload.vendor_id,
            Invoice.invoice_number == payload.invoice_number,
        )
    )

    if existing_invoice:
        raise HTTPException(
            status_code=409,
            detail="Invoice number already exists for this vendor",
        )

    invoice = Invoice(
        nonprofit_id=payload.nonprofit_id,
        vendor_id=payload.vendor_id,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        currency=payload.currency,
        total_amount=Decimal("0.00"),
        status="submitted",
    )

    total_amount = Decimal("0.00")

    for item in payload.line_items:
        line_total = calculate_money(
            item.quantity * item.unit_price
        )

        total_amount += line_total

        invoice.line_items.append(
            InvoiceLineItem(
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=line_total,
                category=item.category,
            )
        )

    invoice.total_amount = calculate_money(
        total_amount
    )

    try:
        db.add(invoice)
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Duplicate invoice detected",
        )

    query = (
        select(Invoice)
        .options(
            selectinload(Invoice.line_items)
        )
        .where(
            Invoice.id == invoice.id
        )
    )

    return db.scalar(query)


@router.get(
    "",
    response_model=list[InvoiceResponse],
)
def list_invoices(
    vendor_id: int | None = None,
    invoice_status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Invoice)
        .options(
            selectinload(Invoice.line_items)
        )
        .where(
            Invoice.nonprofit_id
            == current_user.nonprofit_id
        )
        .order_by(
            Invoice.id.desc()
        )
    )

    if current_user.role == "vendor":
        if current_user.vendor_id is None:
            raise HTTPException(
                status_code=403,
                detail="Vendor account is not linked to a vendor",
            )

        query = query.where(
            Invoice.vendor_id
            == current_user.vendor_id
        )

    elif vendor_id is not None:
        query = query.where(
            Invoice.vendor_id == vendor_id
        )

    if invoice_status is not None:
        query = query.where(
            Invoice.status == invoice_status
        )

    return db.scalars(
        query
    ).unique().all()


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Invoice)
        .options(
            selectinload(Invoice.line_items)
        )
        .where(
            Invoice.id == invoice_id
        )
    )

    invoice = db.scalar(query)

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