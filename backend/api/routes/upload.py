from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from uuid import UUID
from pathlib import Path
import aiofiles
from loguru import logger

from backend.config import get_settings

router = APIRouter()


@router.post("/pid")
async def upload_pid(
    background_tasks: BackgroundTasks,
    unit_id: UUID = Form(...),
    files: list[UploadFile] = File(...),
):
    """Upload one or more P&ID PDF files for a unit. Processing happens in background."""
    settings = get_settings()
    uploaded = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF")

        size = 0
        dest = Path(settings.upload_dir) / str(unit_id) / file.filename
        dest.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(dest, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_size_mb * 1024 * 1024:
                    raise HTTPException(status_code=413, detail=f"{file.filename} exceeds {settings.max_upload_size_mb}MB limit")
                await out.write(chunk)

        logger.info(f"Saved {file.filename} for unit {unit_id} ({size} bytes)")
        uploaded.append({"filename": file.filename, "size": size, "status": "queued"})

        # TODO: enqueue processing job via process_pid_background(unit_id, dest)
        # background_tasks.add_task(process_pid_background, unit_id, str(dest))

    return {"uploaded": len(uploaded), "files": uploaded}


@router.post("/document")
async def upload_document(
    unit_id: UUID = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload a SOP or manual PDF/DOCX for a unit."""
    settings = get_settings()
    allowed = {".pdf", ".docx"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX supported")

    dest = Path(settings.manuals_dir) / str(unit_id) / file.filename
    dest.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(dest, "wb") as out:
        content = await file.read()
        await out.write(content)

    return {"filename": file.filename, "doc_type": doc_type, "status": "queued"}
