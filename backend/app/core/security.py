from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings

EMAIL_SECRET_KEY = settings.email_secret_key

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(str(password)[:72])

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            raise ValueError("Missing subject")
        return str(sub)
    except (JWTError, ValueError) as e:
        raise ValueError("Invalid token") from e

def generate_email_token(user_id, expires_minutes: int = 60, token_type: str = "email_verification"):
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": str(user_id), "exp": expire, "type": token_type}
    return jwt.encode(payload, EMAIL_SECRET_KEY, algorithm="HS256")

def decode_email_token(token: str, token_type: str = "email_verification"):
    try:
        payload = jwt.decode(token, EMAIL_SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != token_type:
            return None
        return payload["sub"]
    except Exception:
        return None
