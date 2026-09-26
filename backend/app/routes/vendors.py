from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.nonprofit import Nonprofit
from app.models.vendor import Vendor
from app.schemas.vendor import (
    VendorCreate,
    VendorResponse,
    VendorUpdate,
)

router = APIRouter(
    prefix="/api/vendors",
    tags=["Vendors"],
)


@router.post(
    "",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
):
    nonprofit = db.get(Nonprofit, payload.nonprofit_id)

    if not nonprofit:
        raise HTTPException(
            status_code=404,
            detail="Nonprofit not found",
        )

    vendor = Vendor(**payload.model_dump())

    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    return vendor


@router.get("", response_model=list[VendorResponse])
def list_vendors(
    nonprofit_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = select(Vendor).order_by(Vendor.id)

    if nonprofit_id is not None:
        query = query.where(
            Vendor.nonprofit_id == nonprofit_id
        )

    return db.scalars(query).all()


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
):
    vendor = db.get(Vendor, vendor_id)

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    return vendor


@router.patch("/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: int,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
):
    vendor = db.get(Vendor, vendor_id)

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    for field, value in payload.model_dump(
        exclude_unset=True
    ).items():
        setattr(vendor, field, value)

    db.commit()
    db.refresh(vendor)

    return vendor


@router.delete(
    "/{vendor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
):
    vendor = db.get(Vendor, vendor_id)

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    db.delete(vendor)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)