from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from backend.db.database import get_db
from backend.db.models import EquipmentTag, Unit, EngineeringDocument
from backend.db.repositories.sop_repo import SOPRepository
from backend.graph.builder import GraphBuilder
from backend.models.equipment import TagSearchResult, EquipmentTagResponse

router = APIRouter()
_graph = GraphBuilder()


@router.get("/tags", response_model=list[TagSearchResult])
async def search_tags(
    q: str = Query(..., min_length=1),
    unit_id: Optional[UUID] = Query(None),
    tag_type: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    semantic: bool = Query(False, description="Use ChromaDB semantic search instead of SQL LIKE"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search equipment tags.
    Default: SQL LIKE on tag name/description (fast, exact-ish).
    semantic=true: ChromaDB vector search (slower but finds related equipment).
    """
    if semantic:
        return await _semantic_search(q, unit_id, tag_type, limit, db)
    return await _sql_search(q, unit_id, tag_type, limit, db)


@router.get("/tags/{tag}", response_model=EquipmentTagResponse)
async def get_tag(
    tag: str,
    unit_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get full details for a specific tag including upstream/downstream neighbours."""
    stmt = select(EquipmentTag, Unit.name.label("unit_name")).join(Unit)
    stmt = stmt.where(EquipmentTag.tag == tag.upper())
    if unit_id:
        stmt = stmt.where(EquipmentTag.unit_id == unit_id)
    stmt = stmt.limit(1)

    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Tag '{tag}' not found")

    eq_tag, unit_name = row
    neighbours = _graph.get_neighbours(unit_name, eq_tag.tag, depth=1)

    return EquipmentTagResponse(
        id=eq_tag.id,
        unit_id=eq_tag.unit_id,
        unit_name=unit_name,
        tag=eq_tag.tag,
        tag_type=eq_tag.tag_type,
        description=eq_tag.description,
        page_number=eq_tag.page_number,
        confidence=eq_tag.confidence,
        raw_attributes=eq_tag.raw_attributes,
        neighbours=neighbours["downstream"] + neighbours["upstream"],
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _sql_search(
    q: str,
    unit_id: Optional[UUID],
    tag_type: Optional[str],
    limit: int,
    db: AsyncSession,
) -> list[TagSearchResult]:
    pattern = f"%{q.upper()}%"
    stmt = (
        select(EquipmentTag, Unit.name.label("unit_name"))
        .join(Unit)
        .where(
            or_(
                EquipmentTag.tag.ilike(pattern),
                EquipmentTag.description.ilike(f"%{q}%"),
            )
        )
    )
    if unit_id:
        stmt = stmt.where(EquipmentTag.unit_id == unit_id)
    if tag_type:
        stmt = stmt.where(EquipmentTag.tag_type == tag_type)
    stmt = stmt.limit(limit)

    rows = await db.execute(stmt)
    return [
        TagSearchResult(
            tag=eq.tag,
            tag_type=eq.tag_type,
            unit_name=unit_name,
            description=eq.description,
            score=1.0,
        )
        for eq, unit_name in rows
    ]


async def _semantic_search(
    q: str,
    unit_id: Optional[UUID],
    tag_type: Optional[str],
    limit: int,
    db: AsyncSession,
) -> list[TagSearchResult]:
    # Resolve unit name(s) for ChromaDB collection lookup
    if unit_id:
        result = await db.execute(select(Unit).where(Unit.id == unit_id))
        unit = result.scalar_one_or_none()
        unit_names = [unit.name] if unit else []
    else:
        result = await db.execute(select(Unit).where(Unit.status == "active"))
        unit_names = [u.name for u in result.scalars().all()]

    from backend.rag.engine import RAGEngine
    rag = RAGEngine()
    results: list[TagSearchResult] = []

    for unit_name in unit_names:
        hits = rag.search_equipment(q, unit_name, n_results=limit)
        for hit in hits:
            # hit["content"] is "{tag} — {type} — {description}"
            parts = hit["content"].split(" — ", 2)
            tag_str = parts[0].strip()
            tag_type_hit = parts[1].strip() if len(parts) > 1 else None
            description = parts[2].strip() if len(parts) > 2 else None
            if tag_type and tag_type_hit != tag_type:
                continue
            results.append(TagSearchResult(
                tag=tag_str,
                tag_type=tag_type_hit,
                unit_name=unit_name,
                description=description,
                score=hit.get("score", 0.0),
            ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


# ── Document endpoints ─────────────────────────────────────────────────────────

@router.get("/documents")
async def list_documents(
    unit_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all indexed SOP/manual documents, optionally filtered by unit."""
    sop_repo = SOPRepository(db)
    docs = await sop_repo.list_by_unit(unit_id) if unit_id else await sop_repo.list_all()
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "filename": d.filename,
            "doc_type": d.doc_type,
            "unit_id": str(d.unit_id) if d.unit_id else None,
            "page_count": d.page_count,
            "indexed": d.indexed,
            "chunk_count": d.chunk_count,
            "uploaded_at": d.uploaded_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/documents/search")
async def search_documents(
    q: str = Query(..., min_length=1),
    unit_id: Optional[UUID] = Query(None),
    n_results: int = Query(5, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Semantic search over indexed SOP and manual documents."""
    if unit_id:
        result = await db.execute(select(Unit).where(Unit.id == unit_id))
        unit = result.scalar_one_or_none()
        unit_names = [unit.name] if unit else []
    else:
        result = await db.execute(select(Unit).where(Unit.status == "active"))
        unit_names = [u.name for u in result.scalars().all()]

    from backend.rag.engine import RAGEngine
    rag = RAGEngine()
    all_results = []

    for unit_name in unit_names:
        hits = rag.search_documents(q, unit_name, n_results=n_results)
        for hit in hits:
            all_results.append({
                "content": hit["content"],
                "source": hit["source"],
                "page": hit.get("page"),
                "unit": unit_name,
            })

    return {"query": q, "results": all_results}


@router.get("/stats/{unit_name}")
async def get_index_stats(unit_name: str):
    """Return ChromaDB collection stats for a unit (equipment + doc chunks indexed)."""
    from backend.rag.engine import RAGEngine
    rag = RAGEngine()
    return rag.get_collection_stats(unit_name)
