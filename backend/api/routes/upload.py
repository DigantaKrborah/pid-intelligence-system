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
