from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from models import User
from schemas import TokenResponse, UserLogin, UserPublic, UserRegister

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user with phone number and password."""

    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(status_code=409, detail="Phone number already registered")

    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id})
    return {"access_token": token, "user": user}


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Login with phone number and password."""

    user = db.query(User).filter(User.phone == payload.phone).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token({"sub": user.id})
    return {"access_token": token, "user": user}


@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.put("/me", response_model=UserPublic)
def update_profile(
    full_name: str = None,
    bio: str = None,
    avatar_url: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the authenticated user's profile."""
    if full_name:
        current_user.full_name = full_name
    if bio is not None:
        current_user.bio = bio
    if avatar_url is not None:
        current_user.avatar_url = avatar_url
    db.commit()
    db.refresh(current_user)
    return current_user
