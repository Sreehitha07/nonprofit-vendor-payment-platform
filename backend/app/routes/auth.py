from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.nonprofit import Nonprofit
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserRegister,
    UserResponse,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: UserRegister,
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

    existing_user = db.scalar(
        select(User).where(
            User.email == payload.email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email is already registered",
        )

    user = User(
        nonprofit_id=payload.nonprofit_id,
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(
            payload.password
        ),
        role=payload.role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post(
    "/token",
    response_model=TokenResponse,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.email == form_data.username
        )
    )

    if not user or not verify_password(
        form_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive",
        )

    token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    return TokenResponse(
        access_token=token
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(
        get_current_user
    ),
):
    return current_user
