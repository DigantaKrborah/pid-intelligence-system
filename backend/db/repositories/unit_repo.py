import uuid
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Unit, PIDDocument, EquipmentTag, EngineeringDocument


class UnitRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, name: str, display_name: str | None, description: str | None) -> Unit:
        unit = Unit(
            name=name.upper().strip(),
            display_name=display_name or name.upper(),
            description=description,
        )
        self.session.add(unit)
        await self.session.flush()
        return unit

    async def get_by_id(self, unit_id: uuid.UUID) -> Unit | None:
        result = await self.session.execute(select(Unit).where(Unit.id == unit_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Unit | None:
        result = await self.session.execute(
            select(Unit).where(Unit.name == name.upper().strip())
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Unit]:
        result = await self.session.execute(
            select(Unit).where(Unit.status == "active").order_by(Unit.name)
        )
        return list(result.scalars().all())

    async def archive(self, unit_id: uuid.UUID) -> bool:
        unit = await self.get_by_id(unit_id)
        if not unit:
            return False
        unit.status = "archived"
        await self.session.flush()
        return True

    async def get_stats(self, unit_id: uuid.UUID) -> dict:
        tag_count = await self.session.scalar(
            select(func.count(EquipmentTag.id)).where(EquipmentTag.unit_id == unit_id)
        )
        doc_count = await self.session.scalar(
            select(func.count(PIDDocument.id)).where(PIDDocument.unit_id == unit_id)
        )
        return {"tag_count": tag_count or 0, "document_count": doc_count or 0}

    async def get_sop_count(self, unit_id: uuid.UUID) -> int:
        count = await self.session.scalar(
            select(func.count(EngineeringDocument.id)).where(EngineeringDocument.unit_id == unit_id)
        )
        return count or 0

    async def get_last_upload(self, unit_id: uuid.UUID) -> datetime | None:
        result = await self.session.scalar(
            select(func.max(PIDDocument.uploaded_at)).where(PIDDocument.unit_id == unit_id)
        )
        return result
