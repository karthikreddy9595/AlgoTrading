from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
argon2_hasher = PasswordHasher()


def create_access_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None,
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate an access token."""
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        return payload
    return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        argon2_hasher.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


def get_password_hash(password: str) -> str:
    return argon2_hasher.hash(password)
