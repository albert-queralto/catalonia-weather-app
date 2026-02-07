from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone

from app.db.session import get_session
from app.db.models import User
from app.services.user.schemas import RegisterIn, TokenOut, MeOut
from app.core.security import hash_password, verify_password, create_access_token, generate_email_token
from app.services.user.auth import get_current_user
from app.services.user.email_utils import send_email

router = APIRouter(prefix="/auth", tags=["auth"])
"""Authentication and user management endpoints."""

@router.post("/register", response_model=MeOut)
def register(payload: RegisterIn, db: Session = Depends(get_session)):
    """
    Register a new user.

    Args:
        payload (RegisterIn): Registration data including email and password.
        db (Session): SQLAlchemy database session.

    Returns:
        MeOut: The registered user's public information.

    Raises:
        HTTPException: If the email is already registered.
    """
    exists = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    u = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="user",
        is_active=True,
        is_verified=False,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    
    token = generate_email_token(u.id)
    u.verification_token = token
    db.commit()
    
    FRONTEND_URL = "http://localhost:5173"
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    send_email(u.email, "Verify your email", f"Click to verify: {verify_url}")

    return MeOut(id=u.id, email=u.email, role=u.role, is_active=u.is_active, is_verified=u.is_verified)  # type: ignore

@router.post("/token", response_model=TokenOut)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_session)):
    """
    Authenticate a user and return a JWT access token.

    Args:
        form (OAuth2PasswordRequestForm): Form data with username (email) and password.
        db (Session): SQLAlchemy database session.

    Returns:
        TokenOut: JWT access token.

    Raises:
        HTTPException: If credentials are invalid or user is inactive.
    """
    # OAuth2PasswordRequestForm uses form fields: username + password
    user = db.execute(select(User).where(User.email == form.username)).scalar_one_or_none()
    if not user or not user.is_active or not verify_password(form.password, user.password_hash) or not user.is_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad credentials")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    jwt_ = create_access_token(subject=str(user.id), expires_minutes=60)
    return TokenOut(access_token=jwt_)

@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's information.

    Args:
        user (User): The current authenticated user (injected by dependency).

    Returns:
        MeOut: The user's public information.
    """
    return MeOut(id=user.id, email=user.email, role=user.role, is_active=user.is_active, is_verified=user.is_verified)  # type: ignore

@router.get("/users")
def list_users(db: Session = Depends(get_session)):
    return db.query(User).all()