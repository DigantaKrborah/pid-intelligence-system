from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pathlib import Path
import aiofiles
from loguru import logger

from backend.config import get_settings
from backend.db.database import get_db
from backend.db.repositories.unit_repo import UnitRepository
from backend.db.repositories.document_repo import DocumentRepository
from backend.db.repositories.sop_repo import SOPRepository
from backend.services.processing import process_pid_document
from backend.services.sop_processor import process_sop_document

router = APIRouter()


@router.post("/pid")
async def upload_pid(
    background_tasks: BackgroundTasks,
    unit_id: UUID = Form(...),
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more P&ID PDF files for a unit. Extraction runs in background."""
    settings = get_settings()

    unit_repo = UnitRepository(db)
    unit = await unit_repo.get_by_id(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    doc_repo = DocumentRepository(db)
    queued = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{file.filename} must be a PDF")

        dest_dir = Path(settings.upload_dir) / str(unit_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / file.filename

        size = 0
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        async with aiofiles.open(dest, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    dest.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"{file.filename} exceeds {settings.max_upload_size_mb} MB limit",
                    )
                await out.write(chunk)

        # Create DB record
        doc = await doc_repo.create_pid_document(
            unit_id=unit_id,
            filename=file.filename,
            original_filename=file.filename,
            file_path=str(dest),
            file_size_bytes=size,
        )
        await db.commit()

        # Queue background processing
        background_tasks.add_task(process_pid_document, doc.id, unit_id)

        logger.info(f"Queued {file.filename} (doc_id={doc.id}) for unit {unit.name}")
        queued.append({"filename": file.filename, "document_id": str(doc.id), "size_bytes": size, "status": "queued"})

    return {"unit": unit.name, "queued_count": len(queued), "files": queued}


@router.post("/document")
async def upload_document(
    background_tasks: BackgroundTasks,
    unit_id: UUID = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a SOP or manual PDF/DOCX for a unit. Text indexing runs in background."""
    settings = get_settings()
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX supported")

    unit_repo = UnitRepository(db)
    unit = await unit_repo.get_by_id(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    dest = Path(settings.manuals_dir) / str(unit_id) / file.filename
    dest.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(dest, "wb") as out:
        await out.write(await file.read())

    # Create DB record
    sop_repo = SOPRepository(db)
    doc = await sop_repo.create(
        unit_id=unit_id,
        filename=file.filename,
        file_path=str(dest),
        doc_type=doc_type,
        title=Path(file.filename).stem.replace("_", " ").replace("-", " ").title(),
    )
    await db.commit()

    # Queue background indexing
    background_tasks.add_task(process_sop_document, doc.id, unit.name)

    logger.info(f"Queued SOP indexing: {file.filename} (doc_id={doc.id}) for unit {unit.name}")
    return {
        "filename": file.filename,
        "document_id": str(doc.id),
        "doc_type": doc_type,
        "unit": unit.name,
        "status": "queued",
    }


@router.get("/recent/{unit_id}")
async def list_recent_uploads(
    unit_id: UUID,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """List the most recent P&ID documents uploaded for a unit (for dashboard)."""
    doc_repo = DocumentRepository(db)
    docs = await doc_repo.list_by_unit(unit_id)
    return [
        {
            "document_id":       str(d.id),
            "filename":          d.original_filename or d.filename,
            "processing_status": d.processing_status,
            "page_count":        d.page_count,
            "tags_extracted":    d.tags_extracted,
            "uploaded_at":       d.uploaded_at.isoformat(),
        }
        for d in docs[:limit]
    ]


@router.get("/status/{document_id}")
async def get_processing_status(document_id: UUID, db: AsyncSession = Depends(get_db)):
    """Poll the processing status of an uploaded P&ID document."""
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": str(doc.id),
        "filename": doc.original_filename,
        "status": doc.processing_status,
        "page_count": doc.page_count,
        "tags_extracted": doc.tags_extracted,
        "error": doc.processing_error,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
    }


@router.get("/list/{unit_id}")
async def list_all_documents(unit_id: UUID, db: AsyncSession = Depends(get_db)):
    """List ALL P&ID documents for a unit (no limit)."""
    doc_repo = DocumentRepository(db)
    docs = await doc_repo.list_by_unit(unit_id)
    return [
        {
            "document_id":       str(d.id),
            "filename":          d.original_filename or d.filename,
            "processing_status": d.processing_status,
            "page_count":        d.page_count or 0,
            "tags_extracted":    d.tags_extracted or 0,
            "uploaded_at":       d.uploaded_at.isoformat(),
        }
        for d in docs
    ]


@router.delete("/pid/{document_id}")
async def delete_pid_document(document_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a P&ID document: removes DB record, graph nodes, ChromaDB embeddings, and file."""
    import shutil
    from sqlalchemy import select as sa_select
    from backend.db.models import EquipmentTag
    from backend.services.graph_service import get_graph_builder
    from backend.rag.engine import RAGEngine

    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    unit_repo = UnitRepository(db)
    unit = await unit_repo.get_by_id(doc.unit_id)
    unit_name = unit.name if unit else ""

    # Collect tag strings before deleting (needed for ChromaDB)
    tag_result = await db.execute(
        sa_select(EquipmentTag.tag).where(EquipmentTag.document_id == document_id)
    )
    tag_strings = [row[0] for row in tag_result.fetchall()]

    # Remove from NetworkX graph
    removed = 0
    if unit_name:
        removed = get_graph_builder().remove_document_nodes(unit_name, str(document_id))

    # Remove from ChromaDB
    if tag_strings and unit_name:
        RAGEngine().delete_tags(unit_name, tag_strings)

    # Delete physical file and page images
    if doc.file_path:
        file_path = Path(doc.file_path)
        file_path.unlink(missing_ok=True)
        pages_dir = file_path.parent / f"{file_path.stem}_pages"
        if pages_dir.exists():
            shutil.rmtree(pages_dir, ignore_errors=True)

    filename = doc.original_filename or doc.filename

    # Explicitly delete equipment_tag rows (FK is SET NULL, not CASCADE)
    from sqlalchemy import delete as sa_delete
    await db.execute(sa_delete(EquipmentTag).where(EquipmentTag.document_id == document_id))

    # Delete DB record
    await db.delete(doc)
    await db.commit()

    logger.info(f"Deleted document {document_id} ({filename}): {removed} graph nodes, {len(tag_strings)} embeddings removed")
    return {
        "deleted":        str(document_id),
        "filename":       filename,
        "tags_removed":   removed,
        "embeds_removed": len(tag_strings),
    }
