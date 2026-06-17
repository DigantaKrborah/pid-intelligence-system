"""
documents.py — Operating manual and SOP upload + tag cross-referencing
POST   /api/documents/upload              → upload a document file
POST   /api/documents/{document_id}/index → find all tag references via LLM (synchronous)
GET    /api/documents                     → list documents with processing status + tag count
GET    /api/documents/{document_id}       → document detail + all tag references

Route order: /upload and /  must come before /{document_id} so FastAPI does not
treat the literal strings "upload" or "" as a document UUID.
"""

import json
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from loguru import logger
from psycopg2.extras import Json
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin, require_operator_or_admin
from app.services.file_service import (
    convert_pdf_to_images,
    copy_image_as_page,
    get_file_type,
    sanitize_folder_name,
    save_upload_file,
    validate_file_type,
)
from app.services.llm_service import LLMService

router = APIRouter()

# Doc types that match the DB CHECK constraint
_VALID_DOC_TYPES = {"OPERATING_MANUAL", "SOP", "DATASHEET", "OTHER"}


# ── LLM prompt for document page tag-finding ──────────────────────────────────

def _build_doc_indexing_prompt(page_number: int, doc_title: str) -> str:
    """
    Build the prompt we send to the LLM for each document page.
    The LLM must return a JSON array — we parse it with parse_json_array_response.
    """
    return f"""You are reading page {page_number} of a refinery document titled "{doc_title}".

Find ALL equipment tags (examples: P-101A, E-201, V-301, TK-101, C-401),
instrument tags (examples: FIC-1001, TT-2015, PCV-3001, LIC-1002, XV-2010), and
line numbers (examples: 6"-HN-1001-150#-A1A) mentioned on this page.

For each tag you find, return one object with these fields:
  - tag_number    : the exact tag as it appears, e.g. "P-101A"
  - page_number   : {page_number}
  - section_title : the section or heading above the tag, or "" if none is visible
  - context_text  : the sentence or short paragraph containing the tag (max 500 characters)
  - context_type  : classify the context — use EXACTLY one of:
                    STARTUP | SHUTDOWN | NORMAL_OPERATION | EMERGENCY | MAINTENANCE | GENERAL

Return ONLY a valid JSON array — no markdown, no explanation, nothing else.
If no tags are found on this page, return an empty array: []

Example:
[
  {{
    "tag_number": "P-101A",
    "page_number": {page_number},
    "section_title": "3.2 Startup Procedure",
    "context_text": "Open the suction valve fully before starting pump P-101A to avoid cavitation.",
    "context_type": "STARTUP"
  }}
]"""


# ── Request body schema for the index endpoint ─────────────────────────────────

class IndexRequest(BaseModel):
    """LLM provider details — api_key is NEVER stored in the database."""
    provider: str    # claude | openai | gemini
    model_name: str  # e.g. claude-sonnet-4-6, gpt-4o, gemini-1.5-pro
    api_key: str     # entered by the user on the Settings page


# ── POST /api/documents/upload ────────────────────────────────────────────────

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    unit_id: str = Form(..., description="UUID of the process unit this document belongs to"),
    doc_type: str = Form(..., description="OPERATING_MANUAL | SOP | DATASHEET | OTHER"),
    doc_title: str = Form(..., description="Human-readable document title"),
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_user: dict = Depends(require_operator_or_admin),
):
    """
    Upload an operating manual, SOP, or datasheet.
    Accepts PDF (preferred) and common image formats.
    File is saved to: UPLOAD_BASE_PATH/manuals/{unit_code}/{original_filename}
    Page extraction for indexing happens later via POST /{document_id}/index.
    """
    settings = get_settings()

    # 1. Validate doc_type
    if doc_type.upper() not in _VALID_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"doc_type must be one of: {', '.join(_VALID_DOC_TYPES)}",
        )

    # 2. Validate file type
    if not validate_file_type(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not allowed. Accepted: pdf, jpg, jpeg, png, tiff",
        )

    file_type = get_file_type(file.filename)

    # 3. Confirm the unit exists
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

    # 4. Build storage path: uploads/manuals/{unit_code}/{original_filename}
    doc_folder = (
        Path(settings.upload_base_path)
        / "manuals"
        / sanitize_folder_name(unit_code)
    )
    file_path = doc_folder / file.filename

    # 5. Save file bytes to disk
    content = await file.read()

    # Enforce 50 MB size limit from CLAUDE.md
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds 50 MB limit.",
        )

    save_upload_file(content, file_path)

    # 6. Insert into documents table
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents
                (unit_id, doc_type, doc_title, original_filename,
                 stored_filepath, file_type, processing_status, uploaded_by)
            VALUES (%s, %s, %s, %s, %s, %s, 'uploaded', %s)
            RETURNING id::text, doc_title, processing_status, uploaded_at
            """,
            (
                unit_id,
                doc_type.upper(),
                doc_title,
                file.filename,
                str(file_path),
                file_type,
                str(current_user["id"]),
            ),
        )
        doc = cur.fetchone()

    document_id = doc["id"]

    # 7. Audit log
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details)
            VALUES (%s, 'UPLOAD_DOCUMENT', 'DOCUMENT', %s, %s)
            """,
            (
                str(current_user["id"]),
                document_id,
                Json({"doc_title": doc_title, "unit_code": unit_code, "file": file.filename}),
            ),
        )

    return {
        "document_id": document_id,
        "doc_title":   doc["doc_title"],
        "status":      doc["processing_status"],
        "uploaded_at": doc["uploaded_at"],
    }


# ── POST /api/documents/{document_id}/index ───────────────────────────────────

@router.post("/{document_id}/index")
def index_document(
    document_id: str,
    payload: IndexRequest,
    db=Depends(get_db),
    current_user: dict = Depends(require_operator_or_admin),
):
    """
    Read every page of the document with the LLM and find all tag references.

    Process per page:
      1. Convert the page to a PNG image (PDF) or use the image directly
      2. Send image to LLM with the tag-finding prompt
      3. Parse the JSON array response
      4. Insert each reference into document_tag_references

    This endpoint is synchronous — it waits for all pages to finish.
    For large documents this may take several minutes.
    """
    settings = get_settings()

    # 1. Fetch the document record
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                doc.id::text, doc.doc_title, doc.doc_type, doc.stored_filepath,
                doc.file_type, doc.unit_id::text,
                pu.unit_code
            FROM documents doc
            JOIN process_units pu ON pu.id = doc.unit_id
            WHERE doc.id = %s
            """,
            (document_id,),
        )
        doc = cur.fetchone()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    stored_path = Path(doc["stored_filepath"])
    if not stored_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document file not found on disk: {stored_path}",
        )

    # 2. Mark as 'processing' immediately
    with db.cursor() as cur:
        cur.execute(
            "UPDATE documents SET processing_status = 'processing' WHERE id = %s",
            (document_id,),
        )

    # 3. Delete old tag references so re-indexing doesn't create duplicates
    with db.cursor() as cur:
        cur.execute(
            "DELETE FROM document_tag_references WHERE document_id = %s",
            (document_id,),
        )

    # 4. Convert the document file to a list of page images
    #    Pages are stored in: uploads/manuals/{unit_code}/pages/{document_id}/
    pages_folder = stored_path.parent / "pages" / document_id
    page_image_paths: list[Path] = []
    conversion_error: Optional[str] = None

    try:
        if doc["file_type"] == "pdf":
            page_image_paths = convert_pdf_to_images(
                pdf_path=stored_path,
                output_folder=pages_folder,
                poppler_path=settings.poppler_path,
            )
        else:
            # Single-image document — treat it as one page
            page_img = copy_image_as_page(stored_path, pages_folder)
            page_image_paths = [page_img]
    except Exception as err:
        conversion_error = str(err)

    if not page_image_paths:
        # Can't convert — mark as failed and return a clear error
        with db.cursor() as cur:
            cur.execute(
                "UPDATE documents SET processing_status = 'failed' WHERE id = %s",
                (document_id,),
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not convert document to images: {conversion_error}",
        )

    # 5. Update total_pages now that we know it
    with db.cursor() as cur:
        cur.execute(
            "UPDATE documents SET total_pages = %s WHERE id = %s",
            (len(page_image_paths), document_id),
        )

    # 6. For each page: call LLM, parse response, insert tag references
    llm = LLMService()
    total_tags_found = 0
    pages_processed  = 0
    failed_pages:    list[int] = []

    for page_num, img_path in enumerate(page_image_paths, start=1):
        prompt = _build_doc_indexing_prompt(page_num, doc["doc_title"])

        try:
            raw_response = llm.analyze_image(
                image_path=img_path,
                prompt=prompt,
                provider=payload.provider,
                model_name=payload.model_name,
                api_key=payload.api_key,
            )
        except Exception as err:
            # LLM failed for this page — log and continue
            logger.error(f"[Documents] Page {page_num} LLM error: {err}")
            failed_pages.append(page_num)
            continue

        # Parse the JSON array the LLM returned
        references = llm.parse_json_array_response(raw_response)

        # Insert each tag reference into the database
        for ref in references:
            tag_num = (ref.get("tag_number") or "").upper().strip()
            if not tag_num:
                continue  # skip blank tags

            # Truncate context_text to 500 chars as the prompt instructs the LLM
            context_text = (ref.get("context_text") or "")[:500]

            try:
                with db.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO document_tag_references
                            (document_id, unit_id, tag_number, page_number,
                             section_title, context_text, context_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            document_id,
                            doc["unit_id"],
                            tag_num,
                            ref.get("page_number", page_num),
                            (ref.get("section_title") or "")[:300],
                            context_text,
                            (ref.get("context_type") or "GENERAL").upper(),
                        ),
                    )
                total_tags_found += 1
            except Exception as err:
                logger.warning(f"[Documents] Could not insert tag '{tag_num}' from page {page_num}: {err}")

        pages_processed += 1

    # 7. Mark as indexed (or failed if every page failed)
    final_status = "indexed" if pages_processed > 0 else "failed"
    with db.cursor() as cur:
        cur.execute(
            "UPDATE documents SET processing_status = %s WHERE id = %s",
            (final_status, document_id),
        )

    # 8. Audit log
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details)
            VALUES (%s, 'INDEX_DOCUMENT', 'DOCUMENT', %s, %s)
            """,
            (
                str(current_user["id"]),
                document_id,
                Json({
                    "provider":        payload.provider,
                    "model_name":      payload.model_name,
                    "pages_processed": pages_processed,
                    "tags_found":      total_tags_found,
                    "failed_pages":    failed_pages,
                }),
            ),
        )

    result: dict = {
        "document_id":      document_id,
        "total_tags_found": total_tags_found,
        "pages_processed":  pages_processed,
        "total_pages":      len(page_image_paths),
        "status":           final_status,
    }

    if failed_pages:
        result["warning"] = f"Pages {failed_pages} failed — run /index again to retry them."

    return result


# ── GET /api/documents ────────────────────────────────────────────────────────

@router.get("/")
def list_documents(
    unit_id: Optional[str] = None,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Return all documents, optionally filtered by unit_id.
    Includes processing status and the total number of tag references indexed.
    """
    params: list = []
    where_clause = ""

    if unit_id:
        where_clause = "WHERE doc.unit_id = %s"
        params.append(unit_id)

    with db.cursor() as cur:
        cur.execute(
            f"""
            SELECT
                doc.id::text             AS id,
                doc.unit_id::text        AS unit_id,
                pu.unit_code,
                pu.unit_name,
                doc.doc_type,
                doc.doc_title,
                doc.original_filename,
                doc.file_type,
                doc.total_pages,
                doc.processing_status,
                doc.uploaded_at,
                COUNT(dtr.id)::int       AS tag_reference_count
            FROM documents doc
            JOIN process_units pu ON pu.id = doc.unit_id
            LEFT JOIN document_tag_references dtr ON dtr.document_id = doc.id
            {where_clause}
            GROUP BY doc.id, doc.unit_id, pu.unit_code, pu.unit_name,
                     doc.doc_type, doc.doc_title, doc.original_filename,
                     doc.file_type, doc.total_pages, doc.processing_status, doc.uploaded_at
            ORDER BY doc.uploaded_at DESC
            """,
            params,
        )
        docs = cur.fetchall()

    return [dict(d) for d in docs]


# ── DELETE /api/documents/{document_id} ──────────────────────────────────────
# Defined before GET /{document_id} — same path, different method, FastAPI handles this fine.

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Delete a document record from the database and remove its file from disk.
    Admin only. Also removes the pages/ subdirectory and all tag references (CASCADE).
    """
    with db.cursor() as cur:
        cur.execute(
            "SELECT stored_filepath, doc_title FROM documents WHERE id = %s",
            (document_id,),
        )
        doc = cur.fetchone()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    stored_path = doc["stored_filepath"]

    # Delete the original file from disk
    if stored_path:
        file_path = Path(stored_path)
        if file_path.exists():
            file_path.unlink()

        # Delete the pages/ folder (where page images are stored after conversion)
        pages_folder = file_path.parent / "pages" / document_id
        if pages_folder.exists():
            shutil.rmtree(pages_folder)

    # Delete the DB row — document_tag_references are removed via ON DELETE CASCADE
    with db.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))

    # Audit log
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details)
            VALUES (%s, 'DELETE_DOCUMENT', 'DOCUMENT', %s, %s)
            """,
            (
                str(current_user["id"]),
                document_id,
                Json({"doc_title": doc["doc_title"]}),
            ),
        )


# ── GET /api/documents/{document_id} ─────────────────────────────────────────
# !! Must be defined AFTER /upload and / to avoid matching those paths !!

@router.get("/{document_id}")
def get_document(
    document_id: str,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Return full document details plus all tag references found in it.
    Tag references are grouped by page number for easy reading.
    """
    # Fetch the document row
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                doc.id::text, doc.unit_id::text,
                pu.unit_code, pu.unit_name,
                doc.doc_type, doc.doc_title,
                doc.original_filename, doc.stored_filepath,
                doc.file_type, doc.total_pages,
                doc.processing_status, doc.uploaded_at
            FROM documents doc
            JOIN process_units pu ON pu.id = doc.unit_id
            WHERE doc.id = %s
            """,
            (document_id,),
        )
        doc = cur.fetchone()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    # Fetch all tag references for this document, ordered for readability
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                id::text, tag_number, page_number,
                section_title, context_text, context_type, created_at
            FROM document_tag_references
            WHERE document_id = %s
            ORDER BY page_number, tag_number
            """,
            (document_id,),
        )
        refs = cur.fetchall()

    result = dict(doc)
    result["tag_references"]      = [dict(r) for r in refs]
    result["tag_reference_count"] = len(refs)
    return result
