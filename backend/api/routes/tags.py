from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

from backend.db.database import get_db
from backend.db.models import EquipmentTag, Unit, PIDDocument
from backend.services.graph_service import get_graph_builder

router = APIRouter()

VALID_TAG_TYPES = {"pump", "vessel", "valve", "instrument", "exchanger", "compressor", "line", "other"}


@router.get("/list/{unit_id}")
async def list_unit_tags(
    unit_id: UUID,
    document_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all equipment tags for a unit with drawing info, optionally filtered by document."""
    stmt = (
        select(
            EquipmentTag.id,
            EquipmentTag.tag,
            EquipmentTag.tag_type,
            EquipmentTag.description,
            EquipmentTag.page_number,
            EquipmentTag.document_id,
            PIDDocument.original_filename.label("drawing"),
        )
        .outerjoin(PIDDocument, EquipmentTag.document_id == PIDDocument.id)
        .where(EquipmentTag.unit_id == unit_id)
        .order_by(EquipmentTag.tag)
    )
    if document_id:
        stmt = stmt.where(EquipmentTag.document_id == document_id)

    rows = (await db.execute(stmt)).fetchall()
    return [
        {
            "id":          str(r.id),
            "tag":         r.tag,
            "tag_type":    r.tag_type or "other",
            "description": r.description or "",
            "page_number": r.page_number or 0,
            "document_id": str(r.document_id) if r.document_id else "",
            "drawing":     r.drawing or "",
        }
        for r in rows
    ]


class TagUpdateRequest(BaseModel):
    tag_type: Optional[str] = None
    description: Optional[str] = None


@router.patch("/{tag_id}")
async def update_tag(tag_id: UUID, body: TagUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Correct a tag's type or description. Syncs change to PostgreSQL and NetworkX graph."""
    result = await db.execute(
        select(EquipmentTag, Unit.name.label("unit_name"))
        .join(Unit, EquipmentTag.unit_id == Unit.id)
        .where(EquipmentTag.id == tag_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Tag not found")

    tag_obj, unit_name = row

    updates: dict = {}
    if body.tag_type is not None:
        if body.tag_type not in VALID_TAG_TYPES:
            raise HTTPException(status_code=422, detail=f"tag_type must be one of {sorted(VALID_TAG_TYPES)}")
        updates["tag_type"] = body.tag_type
    if body.description is not None:
        updates["description"] = body.description.strip()

    if not updates:
        return {"id": str(tag_id), "tag": tag_obj.tag, "changed": 0}

    await db.execute(sa_update(EquipmentTag).where(EquipmentTag.id == tag_id).values(**updates))
    await db.commit()

    # Sync to NetworkX graph node
    gb = get_graph_builder()
    graph = gb.load_or_create(unit_name)
    if tag_obj.tag in graph:
        for k, v in updates.items():
            graph.nodes[tag_obj.tag][k] = v
        gb.save(unit_name)

    return {"id": str(tag_id), "tag": tag_obj.tag, "changed": len(updates), **updates}
