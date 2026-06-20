from pydantic import BaseModel, EmailStr, constr, validator
from typing import Optional, List, Literal
from uuid import UUID
import re

Role = Literal["user", "admin"]

class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    
    @validator("password")
    def password_strong(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain a lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain a special character")
        return v

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MeOut(BaseModel):
    id: UUID
    email: str
    role: Role
    is_active: bool
    is_verified: bool

    notification_preferences: bool = True
    favorite_comarques: List[str] = []

    alert_subscribe_current_location: bool = False
    alert_current_comarca: Optional[str] = None
    alert_meteor_types: List[str] = []
    alert_min_severity: int = 2
    
class UpdateProfileIn(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

    notification_preferences: Optional[bool] = None
    favorite_comarques: Optional[List[str]] = None

    alert_subscribe_current_location: Optional[bool] = None
    alert_current_comarca: Optional[str] = None
    alert_meteor_types: Optional[List[str]] = None
    alert_min_severity: Optional[int] = None

    @validator("password")
    def password_strong(cls, v):
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain a lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain a special character")
        return v
    
class PasswordResetRequestIn(BaseModel):
    email: EmailStr
    
    
class PasswordResetIn(BaseModel):
    token: str
    new_password: str
    
    @validator("new_password")
    def password_strong(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain a lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain a special character")
        return v