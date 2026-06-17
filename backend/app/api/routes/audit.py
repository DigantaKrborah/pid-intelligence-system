"""
audit.py — Audit log viewer
GET /api/audit/ → paginated audit entries (flat list), admin only

Every upload, extraction, search, login, and settings change is recorded in
audit_logs by the other route handlers. This endpoint lets admins view that history.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.database import get_db
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("/")
def get_audit_logs(
    user_id:   Optional[str] = Query(None,  description="Filter by user UUID"),
    action:    Optional[str] = Query(None,  description="Filter by action string, e.g. UPLOAD_DRAWING"),
    date_from: Optional[str] = Query(None,  description="Start date — ISO 8601, e.g. 2025-01-01"),
    date_to:   Optional[str] = Query(None,  description="End date   — ISO 8601, e.g. 2025-12-31"),
    limit:     int           = Query(50,    ge=1, le=1000, description="Max rows to return"),
    offset:    int           = Query(0,     ge=0,          description="Skip this many rows (for pagination)"),
    db=Depends(get_db),
    _=Depends(require_admin),
):
    """
    Return audit log entries newest-first as a flat JSON array.
    Admin only — regular users cannot view the audit trail.

    All filter parameters are optional and can be combined.
    Use limit + offset to page through large result sets.
    Returns a flat list so the frontend can use it directly as an array.
    """

    # Build WHERE clause dynamically — only add conditions for filters that were provided.
    # Using positional %s parameters keeps the query safe from SQL injection.
    conditions = []
    params: list = []

    if user_id:
        conditions.append("al.user_id::text = %s")
        params.append(user_id)

    if action:
        # Allow partial match so "UPLOAD" finds both UPLOAD_DRAWING and UPLOAD_DOCUMENT
        conditions.append("al.action ILIKE %s")
        params.append(f"%{action}%")

    if date_from:
        conditions.append("al.created_at >= %s::timestamptz")
        params.append(date_from)

    if date_to:
        # Include the whole end day by advancing to the start of the next day
        conditions.append("al.created_at < (%s::date + INTERVAL '1 day')::timestamptz")
        params.append(date_to)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Fetch the page of results (LEFT JOIN users so entries survive user deletion)
    with db.cursor() as cur:
        cur.execute(
            f"""
            SELECT
                al.id::text,
                al.action,
                al.entity_type,
                al.entity_id,
                al.details,
                al.ip_address,
                al.created_at,
                al.user_id::text           AS user_id,
                u.username,
                u.full_name,
                u.role                     AS user_role
            FROM audit_logs al
            LEFT JOIN users u ON u.id = al.user_id
            {where_clause}
            ORDER BY al.created_at DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        rows = cur.fetchall()

    # Return a flat list — the frontend paginates by checking len(result) == limit
    return [dict(r) for r in rows]
