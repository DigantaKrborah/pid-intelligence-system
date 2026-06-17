"""
dependencies.py — FastAPI reusable dependencies
Import these with Depends() in any route that needs an authenticated user.

Usage examples:
  @router.get("/admin-only")
  def admin_route(user = Depends(require_admin)):
      ...

  @router.get("/operators-and-admins")
  def operator_route(user = Depends(require_operator_or_admin)):
      ...

  @router.get("/any-logged-in-user")
  def my_route(user = Depends(get_current_user)):
      ...
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import get_db
from app.services.auth_service import decode_token

# HTTPBearer extracts "Bearer <token>" from the Authorization header automatically.
# auto_error=True means it will return 403 if the header is missing entirely.
_http_bearer = HTTPBearer(auto_error=True)


# ── Primary dependency: get the current logged-in user ────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(_http_bearer),
    db=Depends(get_db),
) -> dict:
    """
    FastAPI dependency — validates the JWT token and returns the user row from the DB.
    Raises HTTP 401 if token is invalid/expired or user no longer exists.
    Raises HTTP 401 if the account has been deactivated.
    """
    # 1. Decode the JWT — raises 401 automatically if token is bad
    token_data = decode_token(credentials.credentials)

    # 2. Fetch the user from the database to make sure they still exist and are active
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, org_id, username, full_name, email, role, is_active "
            "FROM users WHERE id = %s",
            (token_data["user_id"],),
        )
        user = cur.fetchone()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated. Contact your administrator.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Return user as a plain dict (RealDictRow works like a dict already)
    return dict(user)


# ── Role-check dependencies ───────────────────────────────────────────────────

def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency — only allows users with role='admin'.
    Use on endpoints that modify system settings, manage users, etc.
    """
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this action.",
        )
    return current_user


def require_operator_or_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency — allows 'admin' and 'operator' roles. Blocks 'viewer'.
    Use on endpoints that upload files, trigger extraction, or modify data.
    """
    if current_user["role"] == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewer accounts cannot perform this action. Contact an admin.",
        )
    return current_user
