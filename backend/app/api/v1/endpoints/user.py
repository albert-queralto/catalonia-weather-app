from app.services.user.email_utils import send_email
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.db.models import User
from app.services.user.schemas import (
    UpdateProfileIn,
    MeOut,
    PasswordResetRequestIn,
    PasswordResetIn
)
from app.core.security import hash_password, decode_email_token
from app.services.user.auth import get_current_user, require_role
from uuid import UUID
import secrets

FRONTEND_URL = "http://localhost:5173"

router = APIRouter(tags=["users"], prefix="/users")

@router.put("/me", response_model=MeOut)
def update_me(
    payload: UpdateProfileIn,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    if payload.email:
        user.email = payload.email
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.notification_preferences is not None:
        user.notification_preferences = payload.notification_preferences
    if payload.favorite_comarques is not None:
        user.favorite_comarques = payload.favorite_comarques
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_session),
    _: User = Depends(require_role("admin"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return

@router.put("/{user_id}/role", response_model=MeOut)
def update_user_role(
    user_id: UUID,
    role: str,
    db: Session = Depends(get_session),
    _: User = Depends(require_role("admin"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    user.role = role
    db.commit()
    db.refresh(user)
    return user

@router.get("/", response_model=list[MeOut])
def list_users(
    db: Session = Depends(get_session),
    _: User = Depends(require_role("admin"))
):
    return db.query(User).all()


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_session)):
    user_id = decode_email_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    db.commit()
    return {"message": "Email verified successfully"}

@router.post("/request-password-reset")
def request_password_reset(payload: PasswordResetRequestIn, db: Session = Depends(get_session)):
    user = db.query(User).filter_by(email=payload.email).first()
    if not user:
        return {"message": "If the email exists, a reset link will be sent."}
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    db.commit()
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    send_email(user.email, "Password Reset", f"Reset your password: {reset_url}")
    return {"message": "If the email exists, a reset link will be sent."}

@router.post("/reset-password")
def reset_password(payload: PasswordResetIn, db: Session = Depends(get_session)):
    user = db.query(User).filter_by(reset_token=payload.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.password_hash = hash_password(payload.new_password)
    user.reset_token = None
    db.commit()
    return {"message": "Password reset successful"}