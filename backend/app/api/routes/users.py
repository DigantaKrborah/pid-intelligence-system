"""
users.py — User management endpoints (admin only)
GET   /api/users/                    → list all users in the organisation
POST  /api/users/                    → create a new user
PATCH /api/users/{user_id}/active    → toggle is_active (enable / disable login)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.services.auth_service import hash_password

router = APIRouter()

_VALID_ROLES = {"admin", "operator", "viewer"}


# ── Request schemas ────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username:  str
    full_name: str
    email:     Optional[str] = None
    role:      str           # admin | operator | viewer
    password:  str           # plain text — hashed before storage


# ── GET /api/users/ ────────────────────────────────────────────────────────────

@router.get("/")
def list_users(
    db=Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Return all users belonging to the same organisation as the calling admin.
    Password hashes are never included in the response.
    """
    org_id = str(current_user["org_id"])

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                id::text, username, full_name, email,
                role, is_active, last_login, created_at
            FROM users
            WHERE org_id = %s
            ORDER BY created_at
            """,
            (org_id,),
        )
        users = cur.fetchall()

    return [dict(u) for u in users]


# ── POST /api/users/ ───────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db=Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Create a new user in the same organisation as the calling admin.
    Hashes the plain-text password with bcrypt before storing it.
    """
    org_id = str(current_user["org_id"])

    # Validate role
    if payload.role not in _VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role must be one of: {', '.join(sorted(_VALID_ROLES))}",
        )

    # Check username uniqueness within this org
    with db.cursor() as cur:
        cur.execute(
            "SELECT id FROM users WHERE org_id = %s AND username = %s",
            (org_id, payload.username.strip()),
        )
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{payload.username}' is already taken.",
            )

    # Hash password before storing — never store plain text
    password_hash = hash_password(payload.password)

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users
                (org_id, username, full_name, email, password_hash, role)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id::text, username, full_name, email, role, is_active, created_at
            """,
            (
                org_id,
                payload.username.strip(),
                payload.full_name.strip(),
                payload.email.strip() if payload.email else None,
                password_hash,
                payload.role,
            ),
        )
        new_user = cur.fetchone()

    return dict(new_user)


# ── PATCH /api/users/{user_id}/active ─────────────────────────────────────────

@router.patch("/{user_id}/active")
def toggle_user_active(
    user_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Flip the is_active flag for a user.
    - If the user was active, they are deactivated (cannot log in).
    - If the user was inactive, they are re-activated.

    Admins cannot deactivate their own account to prevent lockout.
    """
    if str(current_user["id"]) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET is_active = NOT is_active
            WHERE id = %s
            RETURNING id::text, username, is_active
            """,
            (user_id,),
        )
        updated = cur.fetchone()

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    return dict(updated)
