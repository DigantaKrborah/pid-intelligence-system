"""
units.py — Process unit management endpoints
GET  /api/units            → list all active units
POST /api/units            → create a new unit (admin only)
PUT  /api/units/{unit_id}  → update a unit (admin only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin

router = APIRouter()


# ── Request / response shapes ─────────────────────────────────────────────────

class UnitCreate(BaseModel):
    """Body for POST /api/units"""
    unit_code: str           # e.g. CDU, VDU — will be stored uppercase
    unit_name: str           # e.g. Crude Distillation Unit
    description: Optional[str] = None


class UnitUpdate(BaseModel):
    """Body for PUT /api/units/{unit_id} — all fields optional"""
    unit_name: Optional[str] = None
    description: Optional[str] = None


# ── GET /api/units ────────────────────────────────────────────────────────────

@router.get("/")
def list_units(db=Depends(get_db), _=Depends(get_current_user)):
    """
    Return all active process units with a count of drawings uploaded to each.
    Requires a valid login token.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                pu.id::text          AS id,
                pu.unit_code,
                pu.unit_name,
                pu.description,
                pu.is_active,
                pu.created_at,
                COUNT(pd.id)::int    AS drawing_count
            FROM process_units pu
            LEFT JOIN pid_drawings pd ON pd.unit_id = pu.id
            WHERE pu.is_active = true
            GROUP BY pu.id, pu.unit_code, pu.unit_name, pu.description, pu.is_active, pu.created_at
            ORDER BY pu.unit_code
            """
        )
        units = cur.fetchall()

    # Convert RealDictRow objects to plain dicts for JSON serialisation
    return [dict(u) for u in units]


# ── POST /api/units ───────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: UnitCreate,
    db=Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Create a new process unit (e.g. a new refinery unit not in the seed data).
    Admin only. Uses the admin's org_id automatically.
    """
    unit_code = payload.unit_code.upper().strip()

    # Check if unit_code already exists for this organisation
    with db.cursor() as cur:
        cur.execute(
            "SELECT id FROM process_units WHERE org_id = %s AND unit_code = %s",
            (str(current_user["org_id"]), unit_code),
        )
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Unit code '{unit_code}' already exists.",
            )

    # Insert the new unit and return it
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO process_units (org_id, unit_code, unit_name, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id::text, unit_code, unit_name, description, is_active, created_at
            """,
            (str(current_user["org_id"]), unit_code, payload.unit_name, payload.description),
        )
        new_unit = cur.fetchone()

    return dict(new_unit)


# ── PUT /api/units/{unit_id} ──────────────────────────────────────────────────

@router.put("/{unit_id}")
def update_unit(
    unit_id: str,
    payload: UnitUpdate,
    db=Depends(get_db),
    _: dict = Depends(require_admin),
):
    """
    Update the name or description of a process unit.
    Admin only. unit_code cannot be changed after creation.
    """
    # COALESCE keeps the existing value if the payload field is None (not provided)
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE process_units
            SET
                unit_name   = COALESCE(%s, unit_name),
                description = COALESCE(%s, description)
            WHERE id = %s
            RETURNING id::text, unit_code, unit_name, description, is_active, created_at
            """,
            (payload.unit_name, payload.description, unit_id),
        )
        updated = cur.fetchone()

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit '{unit_id}' not found.",
        )

    return dict(updated)
