from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from schemas.schemas import UserCreate, UserOut, TokenOut, LoginRequest
from utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    is_locked_out,
    register_failed_login,
    reset_login_attempts,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken.")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()

    if user and is_locked_out(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again in a few minutes.",
        )

    if not user or not verify_password(payload.password, user.hashed_password):
        if user:
            register_failed_login(user, db)
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    reset_login_attempts(user, db)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token}