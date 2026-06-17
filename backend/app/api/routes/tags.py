"""
tags.py — Tag search and detail endpoints
GET /api/tags/search                     → search by keyword across all tag types
GET /api/tags/unit/{unit_id}/summary     → tag counts per type for a unit
GET /api/tags/unit/{unit_id}/export      → download all tags as CSV
GET /api/tags/{tag_number}               → full detail including connectivity + docs

IMPORTANT: static routes (/search, /unit/...) must be defined BEFORE /{tag_number}
so FastAPI doesn't treat "search" or "unit" as a tag number.
"""

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.core.database import get_db
from app.core.dependencies import get_current_user

router = APIRouter()


# ── GET /api/tags/search ──────────────────────────────────────────────────────

@router.get("/search")
def search_tags(
    q: str = Query("", description="Search text. Leave empty with unit_id to browse all tags for a unit."),
    unit_id: Optional[str] = Query(None, description="Filter by process unit UUID"),
    tag_type: Optional[str] = Query(None, description="Filter category: equipment | instrument | line"),
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Case-insensitive partial search across equipment tags, instrument tags, and line specs.
    When q is empty and unit_id is provided, returns ALL tags for that unit.
    Results include upstream/downstream connectivity counts.
    """
    q = q.strip()
    browsing_all = not q  # no search term → return everything for the unit
    pattern = f"%{q}%"
    row_limit = 200 if browsing_all else 100

    # Build WHERE clauses — skip ILIKE filter when browsing all
    def eq_where():
        clauses = []
        params: list = []
        if not browsing_all:
            clauses.append("(et.tag_number ILIKE %s OR et.description ILIKE %s)")
            params += [pattern, pattern]
        if unit_id:
            clauses.append("et.unit_id::text = %s")
            params.append(unit_id)
        return ("WHERE " + " AND ".join(clauses)) if clauses else "", params

    def inst_where():
        clauses = []
        params: list = []
        if not browsing_all:
            clauses.append("(it.tag_number ILIKE %s OR it.description ILIKE %s)")
            params += [pattern, pattern]
        if unit_id:
            clauses.append("it.unit_id::text = %s")
            params.append(unit_id)
        return ("WHERE " + " AND ".join(clauses)) if clauses else "", params

    def line_where():
        clauses = []
        params: list = []
        if not browsing_all:
            clauses.append("ls.line_number ILIKE %s")
            params.append(pattern)
        if unit_id:
            clauses.append("ls.unit_id::text = %s")
            params.append(unit_id)
        return ("WHERE " + " AND ".join(clauses)) if clauses else "", params

    results = []

    # -- Equipment tags --
    if tag_type in (None, "equipment"):
        w, p = eq_where()
        with db.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    et.tag_number,
                    'EQUIPMENT'     AS tag_category,
                    et.tag_type,
                    et.description,
                    et.service,
                    pu.unit_code,
                    pu.unit_name,
                    d.drawing_number,
                    dp.page_number
                FROM equipment_tags et
                JOIN process_units pu ON pu.id = et.unit_id
                JOIN pid_drawings  d  ON d.id  = et.drawing_id
                JOIN drawing_pages dp ON dp.id = et.page_id
                {w}
                ORDER BY et.tag_number
                LIMIT {row_limit}
                """,
                p,
            )
            results.extend([dict(r) for r in cur.fetchall()])

    # -- Instrument tags --
    if tag_type in (None, "instrument"):
        w, p = inst_where()
        with db.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    it.tag_number,
                    'INSTRUMENT'        AS tag_category,
                    it.instrument_type  AS tag_type,
                    it.description,
                    it.service,
                    pu.unit_code,
                    pu.unit_name,
                    d.drawing_number,
                    dp.page_number
                FROM instrument_tags it
                JOIN process_units pu ON pu.id = it.unit_id
                JOIN pid_drawings  d  ON d.id  = it.drawing_id
                JOIN drawing_pages dp ON dp.id = it.page_id
                {w}
                ORDER BY it.tag_number
                LIMIT {row_limit}
                """,
                p,
            )
            results.extend([dict(r) for r in cur.fetchall()])

    # -- Line specs --
    if tag_type in (None, "line"):
        w, p = line_where()
        with db.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    ls.line_number      AS tag_number,
                    'LINE'              AS tag_category,
                    'LINE_SPEC'         AS tag_type,
                    CONCAT(ls.nominal_diameter, ' ', ls.fluid_service,
                           ' → ', ls.from_equipment, ' to ', ls.to_equipment)
                                        AS description,
                    NULL                AS service,
                    pu.unit_code,
                    pu.unit_name,
                    d.drawing_number,
                    dp.page_number
                FROM line_specs ls
                JOIN process_units pu ON pu.id = ls.unit_id
                JOIN pid_drawings  d  ON d.id  = ls.drawing_id
                JOIN drawing_pages dp ON dp.id = ls.page_id
                {w}
                ORDER BY ls.line_number
                LIMIT {row_limit}
                """,
                p,
            )
            results.extend([dict(r) for r in cur.fetchall()])

    # Sort merged results alphabetically by tag_number
    results.sort(key=lambda r: r.get("tag_number", ""))

    # -- Attach upstream/downstream connectivity for all returned tags --
    if results:
        tag_numbers = [r["tag_number"] for r in results]
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT source_tag, target_tag
                FROM tag_connectivity
                WHERE direction = 'DOWNSTREAM'
                  AND (source_tag = ANY(%s) OR target_tag = ANY(%s))
                  AND (%s IS NULL OR unit_id::text = %s)
                """,
                (tag_numbers, tag_numbers, unit_id, unit_id),
            )
            edges = cur.fetchall()

        downstream_map: dict[str, list[str]] = {}
        upstream_map:   dict[str, list[str]] = {}
        for edge in edges:
            src, tgt = edge["source_tag"], edge["target_tag"]
            downstream_map.setdefault(src, []).append(tgt)
            upstream_map.setdefault(tgt, []).append(src)

        for r in results:
            r["upstream_tags"]   = upstream_map.get(r["tag_number"], [])
            r["downstream_tags"] = downstream_map.get(r["tag_number"], [])
    else:
        for r in results:
            r["upstream_tags"]   = []
            r["downstream_tags"] = []

    return results


# ── GET /api/tags/unit/{unit_id}/summary ──────────────────────────────────────

@router.get("/unit/{unit_id}/summary")
def unit_tag_summary(
    unit_id: str,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """Return tag counts grouped by type for a process unit."""

    # Verify unit exists
    with db.cursor() as cur:
        cur.execute(
            "SELECT unit_code, unit_name FROM process_units WHERE id = %s",
            (unit_id,),
        )
        unit = cur.fetchone()

    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")

    # Equipment tag breakdown
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT tag_type, COUNT(*)::int AS count
            FROM equipment_tags
            WHERE unit_id = %s
            GROUP BY tag_type
            ORDER BY count DESC
            """,
            (unit_id,),
        )
        eq_rows = cur.fetchall()

    # Instrument tag breakdown
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT instrument_type AS tag_type, COUNT(*)::int AS count
            FROM instrument_tags
            WHERE unit_id = %s
            GROUP BY instrument_type
            ORDER BY count DESC
            """,
            (unit_id,),
        )
        inst_rows = cur.fetchall()

    # Line spec count
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*)::int AS count FROM line_specs WHERE unit_id = %s",
            (unit_id,),
        )
        line_count = cur.fetchone()["count"]

    eq_total   = sum(r["count"] for r in eq_rows)
    inst_total = sum(r["count"] for r in inst_rows)

    return {
        "unit_code":  unit["unit_code"],
        "unit_name":  unit["unit_name"],
        "total_tags": eq_total + inst_total + line_count,
        "breakdown": {
            "equipment": {
                "total":  eq_total,
                "by_type": [dict(r) for r in eq_rows],
            },
            "instruments": {
                "total":  inst_total,
                "by_type": [dict(r) for r in inst_rows],
            },
            "lines": {
                "total": line_count,
            },
        },
    }


# ── GET /api/tags/unit/{unit_id}/export ───────────────────────────────────────

@router.get("/unit/{unit_id}/export")
def export_unit_tags_csv(
    unit_id: str,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Download all tags for a unit as a CSV file.
    Columns: tag_number, tag_category, tag_type, description,
             drawing_number, page_number, upstream_tags, downstream_tags
    """
    # Verify unit
    with db.cursor() as cur:
        cur.execute(
            "SELECT unit_code, unit_name FROM process_units WHERE id = %s",
            (unit_id,),
        )
        unit = cur.fetchone()

    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")

    unit_code = unit["unit_code"]

    # Fetch all tags for this unit in one query using UNION
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT et.tag_number, 'EQUIPMENT' AS tag_category, et.tag_type,
                   et.description, d.drawing_number, dp.page_number
            FROM equipment_tags et
            JOIN pid_drawings  d  ON d.id  = et.drawing_id
            JOIN drawing_pages dp ON dp.id = et.page_id
            WHERE et.unit_id = %s

            UNION ALL

            SELECT it.tag_number, 'INSTRUMENT', it.instrument_type,
                   it.description, d.drawing_number, dp.page_number
            FROM instrument_tags it
            JOIN pid_drawings  d  ON d.id  = it.drawing_id
            JOIN drawing_pages dp ON dp.id = it.page_id
            WHERE it.unit_id = %s

            UNION ALL

            SELECT ls.line_number, 'LINE', 'LINE_SPEC',
                   CONCAT(ls.nominal_diameter, ' ', ls.fluid_service),
                   d.drawing_number, dp.page_number
            FROM line_specs ls
            JOIN pid_drawings  d  ON d.id  = ls.drawing_id
            JOIN drawing_pages dp ON dp.id = ls.page_id
            WHERE ls.unit_id = %s

            ORDER BY tag_category, tag_number
            """,
            (unit_id, unit_id, unit_id),
        )
        all_tags = cur.fetchall()

    # Fetch all connectivity for this unit in one query (avoids N+1 problem)
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT source_tag, target_tag, direction, via_line
            FROM tag_connectivity
            WHERE unit_id = %s AND direction = 'DOWNSTREAM'
            """,
            (unit_id,),
        )
        connections = cur.fetchall()

    # Build upstream/downstream lookup maps
    # downstream_map[tag] = ["E-201", "E-202", ...]
    # upstream_map[tag]   = ["TK-101"]
    downstream_map: dict[str, list[str]] = {}
    upstream_map:   dict[str, list[str]] = {}

    for edge in connections:
        src = edge["source_tag"]
        tgt = edge["target_tag"]
        downstream_map.setdefault(src, []).append(tgt)
        upstream_map.setdefault(tgt, []).append(src)

    # Build CSV in memory
    output = io.StringIO()
    fieldnames = [
        "tag_number", "tag_category", "tag_type", "description",
        "drawing_number", "page_number", "upstream_tags", "downstream_tags",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for tag in all_tags:
        tag_num = tag["tag_number"]
        writer.writerow({
            "tag_number":      tag_num,
            "tag_category":    tag["tag_category"],
            "tag_type":        tag["tag_type"] or "",
            "description":     tag["description"] or "",
            "drawing_number":  tag["drawing_number"],
            "page_number":     tag["page_number"],
            "upstream_tags":   "; ".join(upstream_map.get(tag_num, [])),
            "downstream_tags": "; ".join(downstream_map.get(tag_num, [])),
        })

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="tags_{unit_code}.csv"'
        },
    )


# ── GET /api/tags/{tag_number} ────────────────────────────────────────────────
# !! This MUST be defined LAST — it will match any single path segment !!

@router.get("/{tag_number}")
def get_tag_detail(
    tag_number: str,
    unit_id: Optional[str] = Query(None, description="Narrow to a specific unit"),
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Full detail for a tag: description, which drawing it came from,
    upstream/downstream connectivity, and any document references.
    Searches equipment, instrument, and line tables in that order.
    """
    tag_upper = tag_number.upper()

    unit_filter      = "AND et.unit_id::text = %s" if unit_id else ""
    unit_filter_inst = "AND it.unit_id::text = %s" if unit_id else ""
    unit_filter_line = "AND ls.unit_id::text = %s" if unit_id else ""

    params_eq   = (tag_upper, unit_id) if unit_id else (tag_upper,)
    params_inst = (tag_upper, unit_id) if unit_id else (tag_upper,)
    params_line = (tag_upper, unit_id) if unit_id else (tag_upper,)

    tag_row   = None
    tag_cat   = None
    found_uid = None

    # 1. Look in equipment_tags
    with db.cursor() as cur:
        cur.execute(
            f"""
            SELECT et.tag_number, et.tag_type, et.description, et.service,
                   et.design_pressure, et.design_temp, et.capacity, et.material, et.notes,
                   et.unit_id::text AS unit_id,
                   pu.unit_code, pu.unit_name,
                   d.drawing_number, d.drawing_title, d.revision,
                   dp.page_number
            FROM equipment_tags et
            JOIN process_units pu ON pu.id = et.unit_id
            JOIN pid_drawings  d  ON d.id  = et.drawing_id
            JOIN drawing_pages dp ON dp.id = et.page_id
            WHERE et.tag_number = %s {unit_filter}
            """,
            params_eq,
        )
        tag_row = cur.fetchone()
        if tag_row:
            tag_cat = "EQUIPMENT"
            found_uid = tag_row["unit_id"]

    # 2. Look in instrument_tags if not found
    if tag_row is None:
        with db.cursor() as cur:
            cur.execute(
                f"""
                SELECT it.tag_number, it.instrument_type AS tag_type, it.description,
                       it.service, it.process_variable, it.range_low, it.range_high,
                       it.unit_of_measure, it.notes,
                       it.unit_id::text AS unit_id,
                       pu.unit_code, pu.unit_name,
                       d.drawing_number, d.drawing_title, d.revision,
                       dp.page_number
                FROM instrument_tags it
                JOIN process_units pu ON pu.id = it.unit_id
                JOIN pid_drawings  d  ON d.id  = it.drawing_id
                JOIN drawing_pages dp ON dp.id = it.page_id
                WHERE it.tag_number = %s {unit_filter_inst}
                """,
                params_inst,
            )
            tag_row = cur.fetchone()
            if tag_row:
                tag_cat = "INSTRUMENT"
                found_uid = tag_row["unit_id"]

    # 3. Look in line_specs if still not found
    if tag_row is None:
        with db.cursor() as cur:
            cur.execute(
                f"""
                SELECT ls.line_number AS tag_number, 'LINE_SPEC' AS tag_type,
                       CONCAT(ls.nominal_diameter, ' ', ls.fluid_service,
                              ' from ', ls.from_equipment, ' to ', ls.to_equipment) AS description,
                       ls.nominal_diameter, ls.fluid_service, ls.pressure_class,
                       ls.pipe_spec, ls.from_equipment, ls.to_equipment, ls.notes,
                       ls.unit_id::text AS unit_id,
                       pu.unit_code, pu.unit_name,
                       d.drawing_number, d.drawing_title, d.revision,
                       dp.page_number
                FROM line_specs ls
                JOIN process_units pu ON pu.id = ls.unit_id
                JOIN pid_drawings  d  ON d.id  = ls.drawing_id
                JOIN drawing_pages dp ON dp.id = ls.page_id
                WHERE ls.line_number = %s {unit_filter_line}
                """,
                params_line,
            )
            tag_row = cur.fetchone()
            if tag_row:
                tag_cat = "LINE"
                found_uid = tag_row["unit_id"]

    if tag_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag '{tag_number}' not found in any unit.",
        )

    tag_data = dict(tag_row)

    # 4. Upstream connectivity — tags that flow INTO this tag
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                tc.source_tag                                         AS tag_number,
                tc.via_line,
                COALESCE(et.tag_type, it.instrument_type, 'UNKNOWN') AS tag_type,
                COALESCE(et.description, it.description, '')          AS description
            FROM tag_connectivity tc
            LEFT JOIN equipment_tags  et ON et.tag_number = tc.source_tag AND et.unit_id::text = %s
            LEFT JOIN instrument_tags it ON it.tag_number = tc.source_tag AND it.unit_id::text = %s
            WHERE tc.target_tag = %s AND tc.direction = 'DOWNSTREAM'
              AND tc.unit_id::text = %s
            """,
            (found_uid, found_uid, tag_upper, found_uid),
        )
        upstream_tags = [dict(r) for r in cur.fetchall()]

    # 5. Downstream connectivity — tags that this tag flows INTO
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                tc.target_tag                                         AS tag_number,
                tc.via_line,
                COALESCE(et.tag_type, it.instrument_type, 'UNKNOWN') AS tag_type,
                COALESCE(et.description, it.description, '')          AS description
            FROM tag_connectivity tc
            LEFT JOIN equipment_tags  et ON et.tag_number = tc.target_tag AND et.unit_id::text = %s
            LEFT JOIN instrument_tags it ON it.tag_number = tc.target_tag AND it.unit_id::text = %s
            WHERE tc.source_tag = %s AND tc.direction = 'DOWNSTREAM'
              AND tc.unit_id::text = %s
            """,
            (found_uid, found_uid, tag_upper, found_uid),
        )
        downstream_tags = [dict(r) for r in cur.fetchall()]

    # 6. Document references (populated by document indexing — may be empty)
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                doc.doc_title, doc.doc_type,
                dtr.page_number, dtr.section_title, dtr.context_text
            FROM document_tag_references dtr
            JOIN documents doc ON doc.id = dtr.document_id
            WHERE dtr.tag_number = %s AND dtr.unit_id::text = %s
            ORDER BY dtr.page_number
            LIMIT 20
            """,
            (tag_upper, found_uid),
        )
        doc_refs = [dict(r) for r in cur.fetchall()]

    return {
        "tag_number":     tag_data["tag_number"],
        "tag_category":   tag_cat,
        "tag_type":       tag_data.get("tag_type", ""),
        "description":    tag_data.get("description", ""),
        "unit": {
            "unit_code": tag_data["unit_code"],
            "unit_name": tag_data["unit_name"],
        },
        "drawings": [{
            "drawing_number": tag_data["drawing_number"],
            "drawing_title":  tag_data.get("drawing_title", ""),
            "revision":       tag_data.get("revision", ""),
            "page_number":    tag_data["page_number"],
        }],
        "details":          {k: v for k, v in tag_data.items()
                             if k not in ("tag_number", "tag_type", "description",
                                          "unit_id", "unit_code", "unit_name",
                                          "drawing_number", "drawing_title",
                                          "revision", "page_number")},
        "upstream_tags":    upstream_tags,
        "downstream_tags":  downstream_tags,
        "document_references": doc_refs,
    }
