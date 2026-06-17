"""
drawings.py — P&ID drawing upload and management endpoints
POST   /api/drawings/upload          → upload a new P&ID drawing (PDF or image)
GET    /api/drawings                 → list all drawings, optionally filtered by unit
GET    /api/drawings/{drawing_id}    → get drawing details + all pages
DELETE /api/drawings/{drawing_id}    → delete drawing and files from disk (admin only)
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from psycopg2.extras import Json

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin, require_operator_or_admin
from app.services.file_service import (
    convert_pdf_to_images,
    copy_image_as_page,
    delete_drawing_folder,
    get_file_type,
    sanitize_folder_name,
    save_upload_file,
    validate_file_type,
)

router = APIRouter()


# ── POST /api/drawings/upload ─────────────────────────────────────────────────

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_drawing(
    unit_id: str = Form(..., description="UUID of the process unit"),
    drawing_number: str = Form(..., description="Drawing number, e.g. NRL-CDU-PID-001"),
    drawing_title: Optional[str] = Form(None),
    revision: Optional[str] = Form(None, description="e.g. Rev 3, R3"),
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_user: dict = Depends(require_operator_or_admin),
):
    """
    Upload a P&ID drawing (PDF or image).
    - PDF files: each page is converted to a PNG image using Poppler.
    - Image files (jpg/png/tiff): stored as a single page_001.png.
    Files are saved to UPLOAD_BASE_PATH/pid_drawings/{unit_code}/{drawing_number}/
    """
    settings = get_settings()

    # 1. Validate file type
    if not validate_file_type(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Accepted: pdf, jpg, jpeg, png, tiff",
        )

    file_type = get_file_type(file.filename)

    # 2. Confirm the unit exists and get its unit_code (needed for folder naming)
    with db.cursor() as cur:
        cur.execute(
            "SELECT id::text, unit_code FROM process_units WHERE id = %s AND is_active = true",
            (unit_id,),
        )
        unit = cur.fetchone()

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process unit '{unit_id}' not found.",
        )

    unit_code = unit["unit_code"]

    # 3. Build the folder path: uploads/pid_drawings/{unit_code}/{drawing_number}/
    safe_drawing_num = sanitize_folder_name(drawing_number)
    drawing_folder = (
        Path(settings.upload_base_path)
        / "pid_drawings"
        / unit_code
        / safe_drawing_num
    )
    original_file_path = drawing_folder / file.filename

    # 4. Read file bytes and save to disk
    content = await file.read()
    file_size = len(content)
    save_upload_file(content, original_file_path)

    # 5. Convert to page images
    page_image_paths: list[Path] = []
    error_message: Optional[str] = None

    if file_type == "pdf":
        try:
            page_image_paths = convert_pdf_to_images(
                pdf_path=original_file_path,
                output_folder=drawing_folder,
                poppler_path=settings.poppler_path,
            )
        except Exception as err:
            # Don't block the upload — mark as failed, engineer can retry later
            error_message = str(err)

    else:
        # Single-page image — copy as page_001.png for consistent structure
        try:
            page_path = copy_image_as_page(original_file_path, drawing_folder)
            page_image_paths = [page_path]
        except Exception as err:
            error_message = str(err)

    total_pages = len(page_image_paths) if page_image_paths else 1
    upload_status = "completed" if (page_image_paths and not error_message) else (
        "failed" if error_message else "uploaded"
    )

    # 6. Insert the drawing record
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pid_drawings
                (unit_id, drawing_number, drawing_title, revision,
                 original_filename, stored_filepath, file_type,
                 total_pages, upload_status, uploaded_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id::text, drawing_number, drawing_title, total_pages, upload_status, uploaded_at
            """,
            (
                unit_id,
                drawing_number,
                drawing_title,
                revision,
                file.filename,
                str(original_file_path),
                file_type,
                total_pages,
                upload_status,
                str(current_user["id"]),
            ),
        )
        drawing = cur.fetchone()

    drawing_id = drawing["id"]

    # 7. Insert one row per page into drawing_pages
    for page_num, img_path in enumerate(page_image_paths, start=1):
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO drawing_pages
                    (drawing_id, page_number, page_image_path, extraction_status)
                VALUES (%s, %s, %s, 'pending')
                """,
                (drawing_id, page_num, str(img_path)),
            )

    # If conversion failed but no pages were created, insert a placeholder page row
    if not page_image_paths:
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO drawing_pages
                    (drawing_id, page_number, extraction_status)
                VALUES (%s, 1, 'failed')
                """,
                (drawing_id,),
            )

    # 8. Log the upload to audit_logs
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details)
            VALUES (%s, 'UPLOAD_DRAWING', 'DRAWING', %s, %s)
            """,
            (
                str(current_user["id"]),
                drawing_id,
                Json({
                    "drawing_number": drawing_number,
                    "unit_code": unit_code,
                    "file": file.filename,
                    "pages": total_pages,
                }),
            ),
        )

    result = dict(drawing)
    result["drawing_id"] = drawing_id   # convenience alias
    if error_message:
        result["warning"] = f"File saved but page conversion had issues: {error_message}"

    return result


# ── GET /api/drawings ─────────────────────────────────────────────────────────

@router.get("/")
def list_drawings(
    unit_id: Optional[str] = None,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Return all drawings, optionally filtered by unit_id.
    Includes a summary of how many pages have been extracted.
    """
    params: list = []
    where_clause = ""

    if unit_id:
        where_clause = "WHERE d.unit_id = %s"
        params.append(unit_id)

    query = f"""
        SELECT
            d.id::text               AS id,
            d.unit_id::text          AS unit_id,
            pu.unit_code,
            d.drawing_number,
            d.drawing_title,
            d.revision,
            d.total_pages,
            d.upload_status,
            d.original_filename,
            d.file_type,
            d.uploaded_at,
            COUNT(dp.id)::int        AS page_count,
            SUM(CASE WHEN dp.extraction_status = 'completed' THEN 1 ELSE 0 END)::int AS pages_extracted,
            SUM(CASE WHEN dp.extraction_status = 'failed'    THEN 1 ELSE 0 END)::int AS pages_failed
        FROM pid_drawings d
        JOIN process_units pu ON pu.id = d.unit_id
        LEFT JOIN drawing_pages dp ON dp.drawing_id = d.id
        {where_clause}
        GROUP BY d.id, d.unit_id, pu.unit_code, d.drawing_number, d.drawing_title,
                 d.revision, d.total_pages, d.upload_status, d.original_filename,
                 d.file_type, d.uploaded_at
        ORDER BY d.uploaded_at DESC
    """

    with db.cursor() as cur:
        cur.execute(query, params)
        drawings = cur.fetchall()

    return [dict(d) for d in drawings]


# ── GET /api/drawings/{drawing_id}/tags ──────────────────────────────────────
# Must be defined BEFORE /{drawing_id} so FastAPI doesn't try to match "tags" as a drawing_id

@router.get("/{drawing_id}/tags")
def get_drawing_tags(
    drawing_id: str,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Return all extracted tags for a drawing grouped by type.
    Used by the DrawingDetailPage tabs (Equipment, Instruments, Lines, Connectivity).
    """
    # Verify drawing exists
    with db.cursor() as cur:
        cur.execute("SELECT id FROM pid_drawings WHERE id = %s", (drawing_id,))
        if cur.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Drawing '{drawing_id}' not found.",
            )

    # Equipment tags for this drawing
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                et.tag_number, et.tag_type, et.description, et.service,
                et.design_pressure, et.design_temp, et.capacity, et.material, et.notes,
                dp.page_number
            FROM equipment_tags et
            JOIN drawing_pages dp ON dp.id = et.page_id
            WHERE et.drawing_id = %s
            ORDER BY dp.page_number, et.tag_number
            """,
            (drawing_id,),
        )
        equipment = [dict(r) for r in cur.fetchall()]

    # Instrument tags for this drawing
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                it.tag_number, it.instrument_type, it.description,
                it.process_variable, it.service,
                it.range_low, it.range_high, it.unit_of_measure, it.notes,
                dp.page_number
            FROM instrument_tags it
            JOIN drawing_pages dp ON dp.id = it.page_id
            WHERE it.drawing_id = %s
            ORDER BY dp.page_number, it.tag_number
            """,
            (drawing_id,),
        )
        instruments = [dict(r) for r in cur.fetchall()]

    # Line specs for this drawing
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                ls.line_number, ls.nominal_diameter, ls.fluid_service,
                ls.line_sequence, ls.pressure_class, ls.pipe_spec,
                ls.insulation_code, ls.tracing_code,
                ls.from_equipment, ls.to_equipment, ls.notes,
                dp.page_number
            FROM line_specs ls
            JOIN drawing_pages dp ON dp.id = ls.page_id
            WHERE ls.drawing_id = %s
            ORDER BY dp.page_number, ls.line_number
            """,
            (drawing_id,),
        )
        lines = [dict(r) for r in cur.fetchall()]

    # Connectivity edges for this drawing
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT source_tag, source_tag_type, target_tag, target_tag_type,
                   direction, via_line
            FROM tag_connectivity
            WHERE drawing_id = %s
            ORDER BY source_tag, target_tag
            """,
            (drawing_id,),
        )
        connectivity = [dict(r) for r in cur.fetchall()]

    return {
        "equipment":    equipment,
        "instruments":  instruments,
        "lines":        lines,
        "connectivity": connectivity,
    }


# ── GET /api/drawings/{drawing_id} ────────────────────────────────────────────

@router.get("/{drawing_id}")
def get_drawing(
    drawing_id: str,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """Return full drawing details including all its pages and their extraction status."""

    # Get the drawing row
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                d.id::text, d.unit_id::text, pu.unit_code, pu.unit_name,
                d.drawing_number, d.drawing_title, d.revision, d.sheet_number,
                d.original_filename, d.stored_filepath, d.file_type,
                d.total_pages, d.upload_status, d.uploaded_at, d.updated_at
            FROM pid_drawings d
            JOIN process_units pu ON pu.id = d.unit_id
            WHERE d.id = %s
            """,
            (drawing_id,),
        )
        drawing = cur.fetchone()

    if drawing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drawing '{drawing_id}' not found.",
        )

    # Get all pages for this drawing
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                id::text, page_number, page_image_path,
                extraction_status, extracted_at, extraction_model
            FROM drawing_pages
            WHERE drawing_id = %s
            ORDER BY page_number
            """,
            (drawing_id,),
        )
        pages = cur.fetchall()

    result = dict(drawing)
    result["pages"] = [dict(p) for p in pages]
    return result


# ── DELETE /api/drawings/{drawing_id} ─────────────────────────────────────────

@router.delete("/{drawing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_drawing(
    drawing_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Delete a drawing record and remove its files from disk.
    Admin only. Also deletes all drawing_pages rows via CASCADE.
    """
    # Get file path so we can delete it from disk
    with db.cursor() as cur:
        cur.execute(
            "SELECT stored_filepath, drawing_number FROM pid_drawings WHERE id = %s",
            (drawing_id,),
        )
        drawing = cur.fetchone()

    if drawing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drawing '{drawing_id}' not found.",
        )

    stored_path = drawing["stored_filepath"]
    drawing_number = drawing["drawing_number"]

    # Delete the folder from disk (contains original file + all page images)
    if stored_path:
        drawing_folder = Path(stored_path).parent
        delete_drawing_folder(drawing_folder)

    # Delete the DB row (drawing_pages rows are deleted automatically via ON DELETE CASCADE)
    with db.cursor() as cur:
        cur.execute("DELETE FROM pid_drawings WHERE id = %s", (drawing_id,))

    # Log the deletion
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details)
            VALUES (%s, 'DELETE_DRAWING', 'DRAWING', %s, %s)
            """,
            (
                str(current_user["id"]),
                drawing_id,
                Json({"drawing_number": drawing_number}),
            ),
        )
