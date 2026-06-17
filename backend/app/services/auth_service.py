"""
auth_service.py — Password hashing and JWT token helpers
These functions are called by the auth routes and by dependencies.py.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings

# ── Password hashing ──────────────────────────────────────────────────────────
# bcrypt is a slow, secure hashing algorithm designed for passwords.
# CryptContext handles the bcrypt work and future algorithm upgrades.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the plain-text password. Store this in the database."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed: str) -> bool:
    """Return True if plain_password matches the stored bcrypt hash, False otherwise."""
    return _pwd_context.verify(plain_password, hashed)


# ── JWT token creation ────────────────────────────────────────────────────────
# JWT (JSON Web Token) is a signed string that proves the user logged in.
# We embed user_id, username, and role inside the token so we don't have to
# query the database on every single API request.

_ALGORITHM = "HS256"   # signing algorithm (HMAC + SHA-256)


def create_access_token(user_id: str, username: str, role: str) -> str:
    """
    Create and sign a JWT access token.
    The token expires after JWT_EXPIRE_HOURS hours (set in .env).
    Returns the token as a string — send this to the frontend.
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)

    # "payload" is the data stored inside the token (visible if decoded, but tamper-proof)
    payload = {
        "sub": str(user_id),      # "sub" (subject) = the user's UUID
        "username": username,
        "role": role,
        "exp": expire,             # expiry timestamp — jose checks this automatically
    }

    token = jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)
    return token


# ── JWT token decoding ────────────────────────────────────────────────────────

def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Returns a dict with user_id, username, role if valid.
    Raises HTTP 401 if the token is expired, tampered with, or missing fields.
    """
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except JWTError:
        # JWTError covers: expired, bad signature, malformed token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id  = payload.get("sub")
    username = payload.get("username")
    role     = payload.get("role")

    if not user_id or not username or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing required fields.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"user_id": user_id, "username": username, "role": role}
