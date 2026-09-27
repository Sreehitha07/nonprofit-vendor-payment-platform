from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.invoice import Invoice
from app.models.invoice_line_item import InvoiceLineItem
from app.models.nonprofit import Nonprofit
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
    nonprofit_id: int | None = None,
    vendor_id: int | None = None,
    invoice_status: str | None = None,
    db: Session = Depends(get_db),
):
    query = (
        select(Invoice)
        .options(
            selectinload(Invoice.line_items)
        )
        .order_by(
            Invoice.id.desc()
        )
    )

    if nonprofit_id is not None:
        query = query.where(
            Invoice.nonprofit_id == nonprofit_id
        )

    if vendor_id is not None:
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

    return invoice