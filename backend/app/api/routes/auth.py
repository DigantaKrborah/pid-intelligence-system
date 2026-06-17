"""
auth.py — Authentication endpoints
POST /api/auth/login   → verify credentials, return JWT token
GET  /api/auth/me      → return the currently logged-in user's info
POST /api/auth/logout  → tell the frontend to discard its token
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from psycopg2.extras import Json

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.auth_service import create_access_token, verify_password

router = APIRouter()


# ── Request / response shapes ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Body expected by POST /login"""
    username: str
    password: str


class UserOut(BaseModel):
    """User info returned after login or in /me"""
    id: str
    username: str
    full_name: str
    role: str


class LoginResponse(BaseModel):
    """Full response from POST /login"""
    access_token: str
    token_type: str
    user: UserOut


# ── POST /api/auth/login ──────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db=Depends(get_db)):
    """
    Validate username + password.
    On success: return a JWT access token and user info.
    On failure: return 401.
    Also records a LOGIN entry in audit_logs.
    """
    # 1. Look up the user by username
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, username, full_name, password_hash, role, is_active "
            "FROM users WHERE username = %s",
            (payload.username,),
        )
        user = cur.fetchone()

    # 2. Check user exists and password is correct
    #    We use the same error message for both cases to avoid leaking info
    #    (don't tell attackers which of username/password was wrong)
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    # 3. Check account is active
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated. Contact your administrator.",
        )

    user_id = str(user["id"])

    # 4. Update last_login timestamp
    with db.cursor() as cur:
        cur.execute(
            "UPDATE users SET last_login = %s WHERE id = %s",
            (datetime.now(timezone.utc), user_id),
        )

    # 5. Record the login in audit_logs for traceability
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                user_id,
                "LOGIN",
                "USER",
                user_id,
                Json({"username": user["username"]}),  # psycopg2 Json = JSONB safe
            ),
        )

    # 6. Create JWT token
    token = create_access_token(
        user_id=user_id,
        username=user["username"],
        role=user["role"],
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut(
            id=user_id,
            username=user["username"],
            full_name=user["full_name"],
            role=user["role"],
        ),
    )


# ── GET /api/auth/me ──────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
def get_me(current_user: dict = Depends(get_current_user)):
    """
    Return the profile of the currently logged-in user.
    Requires a valid JWT in the Authorization: Bearer <token> header.
    """
    return UserOut(
        id=str(current_user["id"]),
        username=current_user["username"],
        full_name=current_user["full_name"],
        role=current_user["role"],
    )


# ── POST /api/auth/logout ─────────────────────────────────────────────────────

@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    """
    Logout endpoint.
    JWT tokens cannot be invalidated server-side (they are stateless).
    The frontend is responsible for deleting the token from storage.
    We log the action for audit purposes.
    """
    user_id = str(current_user["id"])

    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO audit_logs (user_id, action, entity_type, entity_id) "
            "VALUES (%s, %s, %s, %s)",
            (user_id, "LOGOUT", "USER", user_id),
        )

    return {"message": "Logged out successfully."}
