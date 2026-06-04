from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from backend.db.database import get_db
from backend.db.repositories.unit_repo import UnitRepository
from backend.graph.builder import GraphBuilder
from backend.models.unit import UnitCreate, UnitResponse, UnitStats

router = APIRouter()
_graph = GraphBuilder()


@router.post("/", response_model=UnitResponse, status_code=201)
async def create_unit(payload: UnitCreate, db: AsyncSession = Depends(get_db)):
    """Create a new process unit (e.g. CDU, VDU, HCU)."""
    repo = UnitRepository(db)

    existing = await repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Unit '{payload.name.upper()}' already exists")

    unit = await repo.create(
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
    )
    stats = await repo.get_stats(unit.id)
    return UnitResponse(
        id=unit.id,
        name=unit.name,
        display_name=unit.display_name,
        description=unit.description,
        status=unit.status,
        created_at=unit.created_at,
        updated_at=unit.updated_at,
        **stats,
    )


@router.get("/", response_model=list[UnitResponse])
async def list_units(db: AsyncSession = Depends(get_db)):
    """List all active units with tag and document counts."""
    repo = UnitRepository(db)
    units = await repo.list_active()
    result = []
    for unit in units:
        stats = await repo.get_stats(unit.id)
        result.append(UnitResponse(
            id=unit.id,
            name=unit.name,
            display_name=unit.display_name,
            description=unit.description,
            status=unit.status,
            created_at=unit.created_at,
            updated_at=unit.updated_at,
            **stats,
        ))
    return result


@router.get("/{unit_id}", response_model=UnitStats)
async def get_unit(unit_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get detailed stats for a unit including graph metrics."""
    repo = UnitRepository(db)
    unit = await repo.get_by_id(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    stats = await repo.get_stats(unit_id)
    graph_stats = _graph.get_graph_stats(unit.name)

    return UnitStats(
        unit_id=unit.id,
        unit_name=unit.name,
        total_tags=stats["tag_count"],
        total_documents=stats["document_count"],
        total_sop_documents=0,
        last_upload=None,
        graph_node_count=graph_stats["nodes"],
        graph_edge_count=graph_stats["edges"],
    )


@router.delete("/{unit_id}", status_code=204)
async def archive_unit(unit_id: UUID, db: AsyncSession = Depends(get_db)):
    """Archive a unit (soft delete)."""
    repo = UnitRepository(db)
    success = await repo.archive(unit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Unit not found")
