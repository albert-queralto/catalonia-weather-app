from app.services.user.email_utils import send_email
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.db.models import User
from app.services.user.schemas import (
    UpdateProfileIn,
    MeOut,
    PasswordResetRequestIn,
    PasswordResetIn
)
from app.core.security import hash_password, decode_email_token, generate_email_token
from app.core.config import settings
from app.services.user.auth import get_current_user, require_role
from uuid import UUID

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

    if payload.alert_subscribe_current_location is not None:
        user.alert_subscribe_current_location = payload.alert_subscribe_current_location

    if payload.alert_current_comarca is not None:
        user.alert_current_comarca = payload.alert_current_comarca

    if payload.alert_meteor_types is not None:
        user.alert_meteor_types = payload.alert_meteor_types

    if payload.alert_min_severity is not None:
        if payload.alert_min_severity < 0 or payload.alert_min_severity > 6:
            raise HTTPException(status_code=400, detail="alert_min_severity must be between 0 and 6")
        user.alert_min_severity = payload.alert_min_severity

    db.commit()
    db.refresh(user)

    return user

@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_session),
    admin: User = Depends(require_role("admin"))
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

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
    admin: User = Depends(require_role("admin"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    if user_id == admin.id and role != "admin":
        raise HTTPException(status_code=400, detail="You cannot remove your own admin role")

    user.role = role
    db.commit()
    db.refresh(user)
    return user

@router.put("/{user_id}/active", response_model=MeOut)
def update_user_active(
    user_id: UUID,
    is_active: bool = Query(..., description="Whether the user can sign in"),
    db: Session = Depends(get_session),
    admin: User = Depends(require_role("admin"))
):
    if user_id == admin.id and not is_active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user

@router.put("/{user_id}/verified", response_model=MeOut)
def update_user_verified(
    user_id: UUID,
    is_verified: bool = Query(..., description="Whether the user's email is verified"),
    db: Session = Depends(get_session),
    admin: User = Depends(require_role("admin"))
):
    if user_id == admin.id and not is_verified:
        raise HTTPException(status_code=400, detail="You cannot mark your own account as unverified")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = is_verified
    if is_verified:
        user.verification_token = None
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
    user_id = decode_email_token(token, token_type="email_verification")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.verification_token != token:
        raise HTTPException(status_code=400, detail="Invalid token")
    user.is_verified = True
    user.verification_token = None
    db.commit()
    return {"message": "Email verified successfully"}

@router.post("/request-password-reset")
def request_password_reset(payload: PasswordResetRequestIn, db: Session = Depends(get_session)):
    user = db.query(User).filter_by(email=payload.email).first()
    if not user:
        return {"message": "If the email exists, a reset link will be sent."}
    token = generate_email_token(user.id, expires_minutes=60, token_type="password_reset")
    user.reset_token = token 
    db.commit()
    reset_url = f"{settings.frontend_base_url}/reset-password?token={token}"
    send_email(user.email, "Password Reset", f"Reset your password: {reset_url}")
    return {"message": "If the email exists, a reset link will be sent."}

@router.post("/reset-password")
def reset_password(payload: PasswordResetIn, db: Session = Depends(get_session)):
    user_id = decode_email_token(payload.token, token_type="password_reset")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user or user.reset_token != payload.token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.password_hash = hash_password(payload.new_password)
    user.reset_token = None
    db.commit()
    return {"message": "Password reset successful"}
