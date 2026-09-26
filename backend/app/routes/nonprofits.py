from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.nonprofit import Nonprofit
from app.schemas.nonprofit import (
    NonprofitCreate,
    NonprofitResponse,
    NonprofitUpdate,
)

router = APIRouter(
    prefix="/api/nonprofits",
    tags=["Nonprofits"],
)


@router.post(
    "",
    response_model=NonprofitResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_nonprofit(
    payload: NonprofitCreate,
    db: Session = Depends(get_db),
):
    if payload.registration_number:
        existing = db.scalar(
            select(Nonprofit).where(
                Nonprofit.registration_number == payload.registration_number
            )
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Registration number already exists",
            )

    nonprofit = Nonprofit(**payload.model_dump())

    db.add(nonprofit)
    db.commit()
    db.refresh(nonprofit)

    return nonprofit


@router.get("", response_model=list[NonprofitResponse])
def list_nonprofits(db: Session = Depends(get_db)):
    return db.scalars(
        select(Nonprofit).order_by(Nonprofit.id)
    ).all()


@router.get("/{nonprofit_id}", response_model=NonprofitResponse)
def get_nonprofit(
    nonprofit_id: int,
    db: Session = Depends(get_db),
):
    nonprofit = db.get(Nonprofit, nonprofit_id)

    if not nonprofit:
        raise HTTPException(
            status_code=404,
            detail="Nonprofit not found",
        )

    return nonprofit


@router.patch("/{nonprofit_id}", response_model=NonprofitResponse)
def update_nonprofit(
    nonprofit_id: int,
    payload: NonprofitUpdate,
    db: Session = Depends(get_db),
):
    nonprofit = db.get(Nonprofit, nonprofit_id)

    if not nonprofit:
        raise HTTPException(
            status_code=404,
            detail="Nonprofit not found",
        )

    for field, value in payload.model_dump(
        exclude_unset=True
    ).items():
        setattr(nonprofit, field, value)

    db.commit()
    db.refresh(nonprofit)

    return nonprofit


@router.delete(
    "/{nonprofit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_nonprofit(
    nonprofit_id: int,
    db: Session = Depends(get_db),
):
    nonprofit = db.get(Nonprofit, nonprofit_id)

    if not nonprofit:
        raise HTTPException(
            status_code=404,
            detail="Nonprofit not found",
        )

    db.delete(nonprofit)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)