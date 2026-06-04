from fastapi import APIRouter, Query
from uuid import UUID
from typing import Optional
from backend.models.equipment import TagSearchRequest, TagSearchResult, EquipmentTagResponse

router = APIRouter()


@router.get("/tags", response_model=list[TagSearchResult])
async def search_tags(
    q: str = Query(..., min_length=1),
    unit_id: Optional[UUID] = Query(None),
    tag_type: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
):
    """Full-text + semantic search for equipment tags."""
    # TODO: query PostgreSQL + ChromaDB
    return []


@router.get("/tags/{tag}", response_model=EquipmentTagResponse)
async def get_tag(tag: str, unit_id: Optional[UUID] = Query(None)):
    """Get full details for a specific tag including its graph neighbours."""
    # TODO: fetch from PostgreSQL + GraphBuilder.get_neighbours
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"Tag {tag} not found")
