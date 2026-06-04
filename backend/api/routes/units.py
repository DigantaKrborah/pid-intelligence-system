from fastapi import APIRouter, HTTPException
from uuid import UUID
from backend.models.unit import UnitCreate, UnitResponse, UnitStats

router = APIRouter()


@router.post("/", response_model=UnitResponse, status_code=201)
async def create_unit(payload: UnitCreate):
    """Create a new process unit (e.g. CDU, VDU, HCU)."""
    # TODO: persist to PostgreSQL via unit_repo
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/", response_model=list[UnitResponse])
async def list_units():
    """List all units with tag and document counts."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{unit_id}", response_model=UnitStats)
async def get_unit(unit_id: UUID):
    """Get detailed stats for a unit."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete("/{unit_id}", status_code=204)
async def archive_unit(unit_id: UUID):
    """Archive a unit (soft delete)."""
    raise HTTPException(status_code=501, detail="Not implemented yet")
