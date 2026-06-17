"""
search.py — Global cross-unit search endpoint
GET /api/search/global → search tags and documents across all units

Returns a flat grouped response matching the spec:
  { "equipment": [...], "instruments": [...], "lines": [...], "documents": [...] }

Results within each group are sorted by relevance — exact tag-number match first,
then partial matches, then alphabetically.
"""

from fastapi import APIRouter, Depends, Query

from app.core.database import get_db
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/global")
def global_search(
    q: str = Query(..., min_length=1, description="Search text (partial match)"),
    limit: int = Query(50, ge=1, le=200, description="Max results per group"),
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Search across ALL units and ALL content types in one call.
    Each result includes unit_code so the frontend can show which unit it belongs to.
    """
    pattern       = f"%{q}%"
    exact_pattern = q.upper()   # exact tag-number matches float to the top

    # ── Equipment tags ─────────────────────────────────────────────────────────
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                et.tag_number,
                'EQUIPMENT'     AS tag_category,
                et.tag_type,
                et.description,
                et.service,
                pu.id::text     AS unit_id,
                pu.unit_code,
                pu.unit_name,
                d.drawing_number,
                dp.page_number,
                CASE WHEN et.tag_number = %s THEN 0 ELSE 1 END AS _rank
            FROM equipment_tags et
            JOIN process_units pu ON pu.id = et.unit_id
            JOIN pid_drawings  d  ON d.id  = et.drawing_id
            JOIN drawing_pages dp ON dp.id = et.page_id
            WHERE et.tag_number ILIKE %s
               OR et.description ILIKE %s
               OR et.service     ILIKE %s
            ORDER BY _rank, et.tag_number
            LIMIT %s
            """,
            (exact_pattern, pattern, pattern, pattern, limit),
        )
        equipment = [
            {k: v for k, v in dict(r).items() if k != "_rank"}
            for r in cur.fetchall()
        ]

    # ── Instrument tags ────────────────────────────────────────────────────────
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                it.tag_number,
                'INSTRUMENT'        AS tag_category,
                it.instrument_type  AS tag_type,
                it.description,
                it.service,
                pu.id::text         AS unit_id,
                pu.unit_code,
                pu.unit_name,
                d.drawing_number,
                dp.page_number,
                CASE WHEN it.tag_number = %s THEN 0 ELSE 1 END AS _rank
            FROM instrument_tags it
            JOIN process_units pu ON pu.id = it.unit_id
            JOIN pid_drawings  d  ON d.id  = it.drawing_id
            JOIN drawing_pages dp ON dp.id = it.page_id
            WHERE it.tag_number ILIKE %s
               OR it.description ILIKE %s
               OR it.service     ILIKE %s
            ORDER BY _rank, it.tag_number
            LIMIT %s
            """,
            (exact_pattern, pattern, pattern, pattern, limit),
        )
        instruments = [
            {k: v for k, v in dict(r).items() if k != "_rank"}
            for r in cur.fetchall()
        ]

    # ── Line specs ─────────────────────────────────────────────────────────────
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                ls.line_number      AS tag_number,
                'LINE'              AS tag_category,
                'LINE_SPEC'         AS tag_type,
                CONCAT(ls.nominal_diameter, ' ', ls.fluid_service,
                       ' from ', ls.from_equipment, ' to ', ls.to_equipment) AS description,
                ls.fluid_service    AS service,
                pu.id::text         AS unit_id,
                pu.unit_code,
                pu.unit_name,
                d.drawing_number,
                dp.page_number,
                CASE WHEN ls.line_number = %s THEN 0 ELSE 1 END AS _rank
            FROM line_specs ls
            JOIN process_units pu ON pu.id = ls.unit_id
            JOIN pid_drawings  d  ON d.id  = ls.drawing_id
            JOIN drawing_pages dp ON dp.id = ls.page_id
            WHERE ls.line_number    ILIKE %s
               OR ls.fluid_service  ILIKE %s
               OR ls.from_equipment ILIKE %s
               OR ls.to_equipment   ILIKE %s
            ORDER BY _rank, ls.line_number
            LIMIT %s
            """,
            (exact_pattern, pattern, pattern, pattern, pattern, limit),
        )
        lines = [
            {k: v for k, v in dict(r).items() if k != "_rank"}
            for r in cur.fetchall()
        ]

    # ── Documents ──────────────────────────────────────────────────────────────
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                doc.id::text            AS document_id,
                'DOCUMENT'              AS tag_category,
                doc.doc_type,
                doc.doc_title,
                doc.original_filename,
                doc.processing_status,
                pu.id::text             AS unit_id,
                pu.unit_code,
                pu.unit_name
            FROM documents doc
            JOIN process_units pu ON pu.id = doc.unit_id
            WHERE doc.doc_title        ILIKE %s
               OR doc.original_filename ILIKE %s
               OR doc.doc_type          ILIKE %s
            ORDER BY doc.doc_title
            LIMIT %s
            """,
            (pattern, pattern, pattern, limit),
        )
        documents = [dict(r) for r in cur.fetchall()]

    return {
        "equipment":   equipment,
        "instruments": instruments,
        "lines":       lines,
        "documents":   documents,
    }
