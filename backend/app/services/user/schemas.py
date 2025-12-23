from pydantic import BaseModel, EmailStr
from typing import Literal
from uuid import UUID

Role = Literal["user", "admin"]

class RegisterIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MeOut(BaseModel):
    id: UUID
    email: str
    role: Role
    is_active: bool