import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import PIDDocument, EquipmentTag, TagConnection, ProcessingJob, AuditLog


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pid_document(
        self,
        unit_id: uuid.UUID,
        filename: str,
        original_filename: str,
        file_path: str,
        file_size_bytes: int,
    ) -> PIDDocument:
        doc = PIDDocument(
            unit_id=unit_id,
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            processing_status="queued",
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def get_document(self, doc_id: uuid.UUID) -> PIDDocument | None:
        result = await self.session.execute(
            select(PIDDocument).where(PIDDocument.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def list_by_unit(self, unit_id: uuid.UUID) -> list[PIDDocument]:
        result = await self.session.execute(
            select(PIDDocument)
            .where(PIDDocument.unit_id == unit_id)
            .order_by(PIDDocument.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        doc_id: uuid.UUID,
        status: str,
        error: str | None = None,
        page_count: int | None = None,
        tags_extracted: int | None = None,
    ) -> None:
        values: dict = {"processing_status": status}
        if error:
            values["processing_error"] = error
        if page_count is not None:
            values["page_count"] = page_count
        if tags_extracted is not None:
            values["tags_extracted"] = tags_extracted
        if status == "completed":
            values["completed_at"] = datetime.now(timezone.utc)
        await self.session.execute(
            update(PIDDocument).where(PIDDocument.id == doc_id).values(**values)
        )

    async def upsert_tag(
        self,
        unit_id: uuid.UUID,
        document_id: uuid.UUID,
        tag: str,
        tag_type: str | None,
        description: str | None,
        page_number: int | None,
        confidence: float | None = None,
        raw_attributes: dict | None = None,
    ) -> EquipmentTag:
        result = await self.session.execute(
            select(EquipmentTag).where(
                EquipmentTag.unit_id == unit_id,
                EquipmentTag.tag == tag,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.tag_type = tag_type or existing.tag_type
            existing.description = description or existing.description
            existing.page_number = page_number or existing.page_number
            existing.document_id = document_id
            if confidence is not None:
                existing.confidence = confidence
            if raw_attributes:
                existing.raw_attributes = raw_attributes
            await self.session.flush()
            return existing

        tag_obj = EquipmentTag(
            unit_id=unit_id,
            document_id=document_id,
            tag=tag,
            tag_type=tag_type,
            description=description,
            page_number=page_number,
            confidence=confidence,
            raw_attributes=raw_attributes,
        )
        self.session.add(tag_obj)
        await self.session.flush()
        return tag_obj

    async def get_tag_by_name(self, unit_id: uuid.UUID, tag: str) -> EquipmentTag | None:
        result = await self.session.execute(
            select(EquipmentTag).where(
                EquipmentTag.unit_id == unit_id,
                EquipmentTag.tag == tag,
            )
        )
        return result.scalar_one_or_none()

    async def create_connection(
        self,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        connection_type: str = "pipeline",
        line_number: str | None = None,
    ) -> None:
        conn = TagConnection(
            source_tag_id=source_id,
            target_tag_id=target_id,
            connection_type=connection_type,
            line_number=line_number,
        )
        self.session.add(conn)
        await self.session.flush()

    async def create_processing_job(self, document_id: uuid.UUID, document_type: str = "pid") -> ProcessingJob:
        job = ProcessingJob(document_id=document_id, document_type=document_type, status="queued")
        self.session.add(job)
        await self.session.flush()
        return job

    async def update_job(
        self,
        job_id: uuid.UUID,
        status: str,
        error: str | None = None,
        result_summary: dict | None = None,
    ) -> None:
        values: dict = {"status": status}
        if status == "processing":
            values["started_at"] = datetime.now(timezone.utc)
        if status in ("completed", "failed"):
            values["completed_at"] = datetime.now(timezone.utc)
        if error:
            values["error_message"] = error
        if result_summary:
            values["result_summary"] = result_summary
        await self.session.execute(
            update(ProcessingJob).where(ProcessingJob.id == job_id).values(**values)
        )

    async def get_job(self, job_id: uuid.UUID) -> ProcessingJob | None:
        result = await self.session.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def audit(self, action: str, entity_type: str, entity_id: uuid.UUID, details: dict | None = None) -> None:
        self.session.add(AuditLog(action=action, entity_type=entity_type, entity_id=entity_id, details=details))
        await self.session.flush()
