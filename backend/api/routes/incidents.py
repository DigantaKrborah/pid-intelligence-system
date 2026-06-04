from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from backend.db.database import get_db
from backend.db.models import Incident

router = APIRouter()


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class IncidentCreate(BaseModel):
    unit_id: Optional[UUID] = None
    title: str
    description: str
    severity: str = "medium"          # critical | high | medium | low
    related_tags: list[str] = []


class IncidentResolve(BaseModel):
    resolution: str


class IncidentResponse(BaseModel):
    id: UUID
    unit_id: Optional[UUID]
    title: str
    description: str
    severity: str
    related_tags: list[str]
    status: str
    resolution: Optional[str]
    reported_at: datetime
    resolved_at: Optional[datetime]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=IncidentResponse, status_code=201)
async def create_incident(payload: IncidentCreate, db: AsyncSession = Depends(get_db)):
    """Report a new process incident."""
    incident = Incident(
        unit_id=payload.unit_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        related_tags=payload.related_tags,
        status="open",
    )
    db.add(incident)
    await db.flush()
    await db.commit()
    return _to_response(incident)


@router.get("/", response_model=list[IncidentResponse])
async def list_incidents(
    unit_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List incidents, optionally filtered by unit or status."""
    stmt = select(Incident).order_by(Incident.reported_at.desc())
    if unit_id:
        stmt = stmt.where(Incident.unit_id == unit_id)
    if status:
        stmt = stmt.where(Incident.status == status)
    result = await db.execute(stmt)
    return [_to_response(i) for i in result.scalars().all()]


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single incident by ID."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _to_response(incident)


@router.patch("/{incident_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(
    incident_id: UUID,
    payload: IncidentResolve,
    db: AsyncSession = Depends(get_db),
):
    """Mark an incident as resolved."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status == "resolved":
        raise HTTPException(status_code=409, detail="Incident is already resolved")

    await db.execute(
        update(Incident)
        .where(Incident.id == incident_id)
        .values(
            status="resolved",
            resolution=payload.resolution,
            resolved_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    await db.refresh(incident)
    return _to_response(incident)


@router.delete("/{incident_id}", status_code=204)
async def delete_incident(incident_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete an incident record."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    await db.delete(incident)
    await db.commit()


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_response(i: "Incident") -> IncidentResponse:
    return IncidentResponse(
        id=i.id,
        unit_id=i.unit_id,
        title=i.title,
        description=i.description,
        severity=i.severity,
        related_tags=i.related_tags or [],
        status=i.status,
        resolution=i.resolution,
        reported_at=i.reported_at,
        resolved_at=i.resolved_at,
    )
