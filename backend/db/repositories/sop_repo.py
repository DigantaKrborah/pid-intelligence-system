import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import EngineeringDocument


class SOPRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        unit_id: uuid.UUID,
        filename: str,
        file_path: str,
        doc_type: str,
        title: str | None = None,
    ) -> EngineeringDocument:
        doc = EngineeringDocument(
            unit_id=unit_id,
            filename=filename,
            file_path=file_path,
            doc_type=doc_type,
            title=title or filename,
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def get(self, doc_id: uuid.UUID) -> EngineeringDocument | None:
        result = await self.session.execute(
            select(EngineeringDocument).where(EngineeringDocument.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def list_by_unit(self, unit_id: uuid.UUID) -> list[EngineeringDocument]:
        result = await self.session.execute(
            select(EngineeringDocument)
            .where(EngineeringDocument.unit_id == unit_id)
            .order_by(EngineeringDocument.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[EngineeringDocument]:
        result = await self.session.execute(
            select(EngineeringDocument).order_by(EngineeringDocument.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def mark_indexed(self, doc_id: uuid.UUID, chunk_count: int, page_count: int | None = None) -> None:
        values: dict = {"indexed": True, "chunk_count": chunk_count}
        if page_count is not None:
            values["page_count"] = page_count
        await self.session.execute(
            update(EngineeringDocument)
            .where(EngineeringDocument.id == doc_id)
            .values(**values)
        )
        await self.session.flush()
