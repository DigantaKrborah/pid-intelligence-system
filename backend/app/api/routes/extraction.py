"""
extraction.py — AI tag extraction endpoints
POST /api/extraction/start            → start full-drawing extraction (background)
POST /api/extraction/page             → extract one specific page (synchronous)
GET  /api/extraction/status/{drawing_id} → check page-by-page progress
POST /api/extraction/retry/{page_id}  → retry a failed page
"""

import json
import psycopg2
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from psycopg2.extras import Json, RealDictCursor
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_operator_or_admin
from app.services.llm_service import LLMService

router = APIRouter()


# ── Shared request body ───────────────────────────────────────────────────────

class ExtractionRequest(BaseModel):
    """LLM provider details — api_key is NEVER stored in the database."""
    provider: str     # claude | openai | gemini
    model_name: str   # e.g. claude-sonnet-4-6, gpt-4o, gemini-1.5-pro
    api_key: str      # entered by the user in the Settings page


class StartExtractionRequest(ExtractionRequest):
    drawing_id: str


class PageExtractionRequest(ExtractionRequest):
    page_id: str


# ── Core extraction logic (shared by routes and background task) ───────────────

def _extract_page_with_conn(
    db_conn,
    page_id: str,
    provider: str,
    model_name: str,
    api_key: str,
) -> dict:
    """
    Extract all tags from a single drawing page and store them in the database.
    Uses an existing psycopg2 connection (works both in routes and background tasks).
    Returns a summary dict with tag counts.
    """
    # 1. Fetch page details + drawing + unit info in one query
    with db_conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                dp.id::text           AS page_id,
                dp.page_number,
                dp.page_image_path,
                dp.drawing_id::text   AS drawing_id,
                d.drawing_number,
                d.drawing_title,
                d.unit_id::text       AS unit_id,
                pu.unit_name,
                pu.unit_code
            FROM drawing_pages dp
            JOIN pid_drawings d  ON d.id  = dp.drawing_id
            JOIN process_units pu ON pu.id = d.unit_id
            WHERE dp.id = %s
            """,
            (page_id,),
        )
        page = cur.fetchone()

    if page is None:
        raise ValueError(f"Page '{page_id}' not found in database.")

    image_path = page["page_image_path"]
    if not image_path or not Path(image_path).exists():
        raise FileNotFoundError(
            f"Image file not found: {image_path}. "
            "Was the drawing uploaded and converted successfully?"
        )

    # 2. Mark the page as 'processing' so the UI can show a spinner
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE drawing_pages SET extraction_status = 'processing' WHERE id = %s",
            (page_id,),
        )
    db_conn.commit()

    # 3. Build drawing context dict for the prompt
    drawing_context = {
        "unit_name":      page["unit_name"],
        "drawing_number": page["drawing_number"],
        "drawing_title":  page["drawing_title"] or "",
        "page_number":    page["page_number"],
    }

    # 4. Call the LLM — this may take 15–60 seconds depending on drawing complexity
    llm = LLMService()
    raw_response = llm.extract_from_image(
        image_path=image_path,
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        drawing_context=drawing_context,
    )

    # 5. Parse the JSON response
    extracted = llm.parse_llm_response(raw_response)

    # 6. Delete any previously extracted data for this page (supports retry)
    unit_id   = page["unit_id"]
    drawing_id = page["drawing_id"]

    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM equipment_tags  WHERE page_id = %s", (page_id,))
        cur.execute("DELETE FROM instrument_tags WHERE page_id = %s", (page_id,))
        cur.execute("DELETE FROM line_specs      WHERE page_id = %s", (page_id,))

    # 7. Insert equipment tags
    eq_count = 0
    for item in extracted.get("equipment_tags", []):
        tag_num = (item.get("tag_number") or "").upper().strip()
        if not tag_num:
            continue
        try:
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO equipment_tags
                        (unit_id, drawing_id, page_id, tag_number, tag_type, description,
                         service, design_pressure, design_temp, capacity, material, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (unit_id, tag_number) DO UPDATE SET
                        drawing_id      = EXCLUDED.drawing_id,
                        page_id         = EXCLUDED.page_id,
                        tag_type        = EXCLUDED.tag_type,
                        description     = EXCLUDED.description,
                        service         = EXCLUDED.service,
                        design_pressure = EXCLUDED.design_pressure,
                        design_temp     = EXCLUDED.design_temp,
                        capacity        = EXCLUDED.capacity,
                        material        = EXCLUDED.material,
                        notes           = EXCLUDED.notes
                    """,
                    (
                        unit_id, drawing_id, page_id, tag_num,
                        item.get("tag_type", ""),
                        item.get("description", ""),
                        item.get("service", ""),
                        item.get("design_pressure", ""),
                        item.get("design_temp", ""),
                        item.get("capacity", ""),
                        item.get("material", ""),
                        item.get("notes", ""),
                    ),
                )
            eq_count += 1
        except Exception as e:
            logger.warning(f"Could not insert equipment tag '{tag_num}': {e}")

    # 8. Insert instrument tags
    inst_count = 0
    for item in extracted.get("instrument_tags", []):
        tag_num = (item.get("tag_number") or "").upper().strip()
        if not tag_num:
            continue
        try:
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO instrument_tags
                        (unit_id, drawing_id, page_id, tag_number, instrument_type,
                         description, process_variable, service,
                         range_low, range_high, unit_of_measure, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (unit_id, tag_number) DO UPDATE SET
                        drawing_id       = EXCLUDED.drawing_id,
                        page_id          = EXCLUDED.page_id,
                        instrument_type  = EXCLUDED.instrument_type,
                        description      = EXCLUDED.description,
                        process_variable = EXCLUDED.process_variable,
                        service          = EXCLUDED.service,
                        range_low        = EXCLUDED.range_low,
                        range_high       = EXCLUDED.range_high,
                        unit_of_measure  = EXCLUDED.unit_of_measure,
                        notes            = EXCLUDED.notes
                    """,
                    (
                        unit_id, drawing_id, page_id, tag_num,
                        item.get("instrument_type", ""),
                        item.get("description", ""),
                        item.get("process_variable", ""),
                        item.get("service", ""),
                        item.get("range_low", ""),
                        item.get("range_high", ""),
                        item.get("unit_of_measure", ""),
                        item.get("notes", ""),
                    ),
                )
            inst_count += 1
        except Exception as e:
            logger.warning(f"Could not insert instrument tag '{tag_num}': {e}")

    # 9. Insert line specs (no unique constraint — delete old ones above)
    line_count = 0
    for item in extracted.get("line_specs", []):
        line_num = (item.get("line_number") or "").strip()
        if not line_num:
            continue
        try:
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO line_specs
                        (unit_id, drawing_id, page_id, line_number, nominal_diameter,
                         fluid_service, line_sequence, pressure_class, pipe_spec,
                         insulation_code, tracing_code, from_equipment, to_equipment, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        unit_id, drawing_id, page_id, line_num,
                        item.get("nominal_diameter", ""),
                        item.get("fluid_service", ""),
                        item.get("line_sequence", ""),
                        item.get("pressure_class", ""),
                        item.get("pipe_spec", ""),
                        item.get("insulation_code", ""),
                        item.get("tracing_code", ""),
                        item.get("from_equipment", ""),
                        item.get("to_equipment", ""),
                        item.get("notes", ""),
                    ),
                )
            line_count += 1
        except Exception as e:
            logger.warning(f"Could not insert line spec '{line_num}': {e}")

    # 10. Insert connectivity edges (drawing-level, not page-level in schema)
    conn_count = 0
    for edge in extracted.get("connectivity", []):
        src = (edge.get("source_tag") or "").upper().strip()
        tgt = (edge.get("target_tag") or "").upper().strip()
        if not src or not tgt:
            continue
        try:
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tag_connectivity
                        (unit_id, drawing_id, source_tag, source_tag_type,
                         target_tag, target_tag_type, direction, via_line)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        unit_id, drawing_id, src,
                        edge.get("source_tag_type", "EQUIPMENT"),
                        tgt,
                        edge.get("target_tag_type", "EQUIPMENT"),
                        edge.get("direction", "DOWNSTREAM"),
                        edge.get("via_line", ""),
                    ),
                )
            conn_count += 1
        except Exception as e:
            logger.warning(f"Could not insert connectivity {src}→{tgt}: {e}")

    # 11. Mark page as completed and store raw LLM response for audit
    with db_conn.cursor() as cur:
        cur.execute(
            """
            UPDATE drawing_pages
            SET extraction_status  = 'completed',
                extracted_at       = NOW(),
                extraction_model   = %s,
                raw_llm_response   = %s
            WHERE id = %s
            """,
            (f"{provider}/{model_name}", json.dumps(extracted), page_id),
        )

    db_conn.commit()
    logger.info(
        f"Page {page['page_number']} done: "
        f"{eq_count} equipment, {inst_count} instruments, "
        f"{line_count} lines, {conn_count} connections"
    )

    return {
        "page_id":           page_id,
        "page_number":       page["page_number"],
        "equipment_count":   eq_count,
        "instrument_count":  inst_count,
        "line_count":        line_count,
        "connectivity_count": conn_count,
    }


def _run_drawing_extraction_bg(
    drawing_id: str,
    page_ids: list[str],
    provider: str,
    model_name: str,
    api_key: str,
    user_id: str,
) -> None:
    """
    Background task: extract all pages of a drawing one by one.
    Opens its own database connection so it can run after the HTTP response is sent.
    """
    settings = get_settings()
    logger.info(f"[BG] Starting extraction for drawing {drawing_id} — {len(page_ids)} page(s)")

    # Create a direct connection (not from the pool) for the background task
    db_conn = psycopg2.connect(settings.database_url)
    db_conn.autocommit = False

    try:
        for page_id in page_ids:
            try:
                _extract_page_with_conn(db_conn, page_id, provider, model_name, api_key)
            except Exception as err:
                # Mark this page as failed but continue with remaining pages
                logger.error(f"[BG] Page {page_id} FAILED: {err}")
                with db_conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE drawing_pages
                        SET extraction_status = 'failed',
                            raw_llm_response  = %s
                        WHERE id = %s
                        """,
                        (f"ERROR: {err}", page_id),
                    )
                db_conn.commit()

        # Mark the parent drawing as completed
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE pid_drawings SET upload_status = 'completed' WHERE id = %s",
                (drawing_id,),
            )
        db_conn.commit()
        logger.info(f"[BG] Drawing {drawing_id} extraction complete.")

    except Exception as err:
        db_conn.rollback()
        logger.error(f"[BG] Fatal error extracting drawing {drawing_id}: {err}")
    finally:
        db_conn.close()


# ── POST /api/extraction/start ────────────────────────────────────────────────

@router.post("/start")
def start_extraction(
    payload: StartExtractionRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_user: dict = Depends(require_operator_or_admin),
):
    """
    Queue extraction for ALL pages of a drawing.
    Returns immediately — extraction runs in the background.
    Poll GET /api/extraction/status/{drawing_id} to track progress.
    """
    # Get pages that need extraction (pending or previously failed)
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id::text AS id, page_number
            FROM drawing_pages
            WHERE drawing_id = %s
              AND extraction_status IN ('pending', 'failed')
            ORDER BY page_number
            """,
            (payload.drawing_id,),
        )
        pages = cur.fetchall()

    if not pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pages found for this drawing, or all pages are already extracted.",
        )

    page_ids = [p["id"] for p in pages]

    # Mark drawing as 'processing' immediately so the UI can show it
    with db.cursor() as cur:
        cur.execute(
            "UPDATE pid_drawings SET upload_status = 'processing' WHERE id = %s",
            (payload.drawing_id,),
        )

    # Queue the background task — runs after this response is sent
    background_tasks.add_task(
        _run_drawing_extraction_bg,
        drawing_id=payload.drawing_id,
        page_ids=page_ids,
        provider=payload.provider,
        model_name=payload.model_name,
        api_key=payload.api_key,
        user_id=str(current_user["id"]),
    )

    return {
        "message": "Extraction started",
        "drawing_id": payload.drawing_id,
        "total_pages": len(page_ids),
        "note": "Poll GET /api/extraction/status/{drawing_id} to track progress.",
    }


# ── POST /api/extraction/page ─────────────────────────────────────────────────

@router.post("/page")
def extract_single_page(
    payload: PageExtractionRequest,
    db=Depends(get_db),
    _: dict = Depends(require_operator_or_admin),
):
    """
    Extract tags from a single drawing page synchronously.
    Note: This request may take 15–60 seconds while waiting for the LLM.
    The frontend should show a loading indicator and set a generous timeout.
    """
    try:
        result = _extract_page_with_conn(
            db_conn=db,
            page_id=payload.page_id,
            provider=payload.provider,
            model_name=payload.model_name,
            api_key=payload.api_key,
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except RuntimeError as err:
        # LLM API error — mark the page as failed
        with db.cursor() as cur:
            cur.execute(
                "UPDATE drawing_pages SET extraction_status = 'failed', "
                "raw_llm_response = %s WHERE id = %s",
                (f"ERROR: {err}", payload.page_id),
            )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(err))

    return result


# ── GET /api/extraction/status/{drawing_id} ───────────────────────────────────

@router.get("/status/{drawing_id}")
def get_extraction_status(
    drawing_id: str,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Return the extraction status for every page of a drawing.
    Use this to poll progress after calling /start.
    """
    # Drawing-level summary
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id::text, drawing_number, drawing_title, upload_status, total_pages
            FROM pid_drawings WHERE id = %s
            """,
            (drawing_id,),
        )
        drawing = cur.fetchone()

    if drawing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drawing '{drawing_id}' not found.",
        )

    # Per-page status
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                id::text, page_number, extraction_status,
                extraction_model, extracted_at
            FROM drawing_pages
            WHERE drawing_id = %s
            ORDER BY page_number
            """,
            (drawing_id,),
        )
        pages = cur.fetchall()

    # Count tags already extracted
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*)::int FROM equipment_tags  WHERE drawing_id = %s", (drawing_id,)
        )
        eq_total = cur.fetchone()["count"]

        cur.execute(
            "SELECT COUNT(*)::int FROM instrument_tags WHERE drawing_id = %s", (drawing_id,)
        )
        inst_total = cur.fetchone()["count"]

        cur.execute(
            "SELECT COUNT(*)::int FROM line_specs       WHERE drawing_id = %s", (drawing_id,)
        )
        line_total = cur.fetchone()["count"]

    return {
        "drawing":          dict(drawing),
        "pages":            [dict(p) for p in pages],
        "tags_extracted": {
            "equipment":    eq_total,
            "instruments":  inst_total,
            "lines":        line_total,
        },
    }


# ── POST /api/extraction/retry/{page_id} ─────────────────────────────────────

@router.post("/retry/{page_id}")
def retry_page_extraction(
    page_id: str,
    payload: ExtractionRequest,
    db=Depends(get_db),
    _: dict = Depends(require_operator_or_admin),
):
    """
    Retry extraction for a single page that previously failed.
    Deletes old data for this page and re-runs the LLM extraction.
    """
    # Confirm the page exists and check its current status
    with db.cursor() as cur:
        cur.execute(
            "SELECT id::text, extraction_status FROM drawing_pages WHERE id = %s",
            (page_id,),
        )
        page = cur.fetchone()

    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page '{page_id}' not found.",
        )

    # Reset status to pending so _extract_page_with_conn can process it
    with db.cursor() as cur:
        cur.execute(
            "UPDATE drawing_pages SET extraction_status = 'pending' WHERE id = %s",
            (page_id,),
        )

    # Re-run extraction (synchronous — may take up to a minute)
    try:
        result = _extract_page_with_conn(
            db_conn=db,
            page_id=page_id,
            provider=payload.provider,
            model_name=payload.model_name,
            api_key=payload.api_key,
        )
    except Exception as err:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE drawing_pages SET extraction_status = 'failed', "
                "raw_llm_response = %s WHERE id = %s",
                (f"RETRY ERROR: {err}", page_id),
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retry failed: {err}",
        )

    return {**result, "message": "Retry successful"}
