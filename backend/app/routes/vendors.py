from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
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
from app.models.nonprofit import Nonprofit
from app.models.user import User
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
    current_user: User = Depends(
        require_roles(
            "staff",
            "manager",
            "admin",
        )
    ),
):
    if payload.nonprofit_id != current_user.nonprofit_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot create vendors for another nonprofit",
        )

    nonprofit = db.get(
        Nonprofit,
        payload.nonprofit_id,
    )

    if not nonprofit:
        raise HTTPException(
            status_code=404,
            detail="Nonprofit not found",
        )

    vendor = Vendor(
        **payload.model_dump()
    )

    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    return vendor


@router.get(
    "",
    response_model=list[VendorResponse],
)
def list_vendors(
    nonprofit_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    if (
        nonprofit_id is not None
        and nonprofit_id != current_user.nonprofit_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this nonprofit",
        )

    query = select(Vendor).where(
        Vendor.nonprofit_id
        == current_user.nonprofit_id
    )

    if current_user.role == "vendor":
        if current_user.vendor_id is None:
            raise HTTPException(
                status_code=403,
                detail="Vendor account is not linked to a vendor",
            )

        query = query.where(
            Vendor.id == current_user.vendor_id
        )

    return db.scalars(
        query.order_by(Vendor.id)
    ).all()


@router.get(
    "/{vendor_id}",
    response_model=VendorResponse,
)
def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    vendor = db.get(
        Vendor,
        vendor_id,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    ensure_vendor_access(
        current_user,
        vendor.id,
        vendor.nonprofit_id,
    )

    return vendor


@router.patch(
    "/{vendor_id}",
    response_model=VendorResponse,
)
def update_vendor(
    vendor_id: int,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "staff",
            "manager",
            "admin",
        )
    ),
):
    vendor = db.get(
        Vendor,
        vendor_id,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    if vendor.nonprofit_id != current_user.nonprofit_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this vendor",
        )

    for field, value in payload.model_dump(
        exclude_unset=True
    ).items():
        setattr(
            vendor,
            field,
            value,
        )

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
    current_user: User = Depends(
        require_roles(
            "manager",
            "admin",
        )
    ),
):
    vendor = db.get(
        Vendor,
        vendor_id,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    if vendor.nonprofit_id != current_user.nonprofit_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this vendor",
        )

    db.delete(vendor)
    db.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )