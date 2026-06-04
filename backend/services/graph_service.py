"""
Graph resilience service — rebuild NetworkX graph from PostgreSQL when JSON is missing.
Called automatically during startup if a unit's graph file doesn't exist.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.db.models import Unit, EquipmentTag, TagConnection
from backend.graph.builder import GraphBuilder

_graph = GraphBuilder()


async def rebuild_graph_from_db(unit_name: str, db: AsyncSession) -> int:
    """
    Rebuild a unit's NetworkX graph from PostgreSQL data.
    Returns the number of nodes added.
    Used when graph JSON file is missing (e.g. first run, volume lost).
    """
    # Fetch unit
    result = await db.execute(select(Unit).where(Unit.name == unit_name.upper()))
    unit = result.scalar_one_or_none()
    if not unit:
        logger.warning(f"rebuild_graph_from_db: unit '{unit_name}' not found")
        return 0

    # Fetch all tags for this unit
    tag_result = await db.execute(
        select(EquipmentTag).where(EquipmentTag.unit_id == unit.id)
    )
    tags = tag_result.scalars().all()

    if not tags:
        logger.info(f"No tags found for unit {unit_name} — empty graph")
        return 0

    # Build tag id → tag name map for connection lookup
    id_to_tag = {t.id: t.tag for t in tags}

    # Fetch all connections for tags in this unit
    tag_ids = [t.id for t in tags]
    conn_result = await db.execute(
        select(TagConnection).where(TagConnection.source_tag_id.in_(tag_ids))
    )
    connections = conn_result.scalars().all()

    # Rebuild graph
    tags_data = [
        {
            "tag": t.tag,
            "tag_type": t.tag_type or "other",
            "description": t.description or "",
            "document_id": str(t.document_id) if t.document_id else "",
            "page_number": t.page_number or 0,
        }
        for t in tags
    ]
    connections_data = [
        {
            "source": id_to_tag[c.source_tag_id],
            "target": id_to_tag[c.target_tag_id],
            "connection_type": c.connection_type or "pipeline",
            "line_number": c.line_number or "",
        }
        for c in connections
        if c.source_tag_id in id_to_tag and c.target_tag_id in id_to_tag
    ]

    _graph.rebuild_from_tags(unit_name, tags_data, connections_data)
    logger.info(f"Rebuilt graph for {unit_name}: {len(tags)} nodes, {len(connections)} edges")
    return len(tags)


async def ensure_all_graphs_loaded(db: AsyncSession) -> None:
    """
    On startup, check each active unit — if its graph JSON is missing,
    rebuild from PostgreSQL. Called from main.py lifespan.
    """
    result = await db.execute(select(Unit).where(Unit.status == "active"))
    units = result.scalars().all()

    for unit in units:
        path = _graph._graph_path(unit.name)
        if not path.exists():
            logger.info(f"Graph JSON missing for {unit.name} — rebuilding from DB")
            await rebuild_graph_from_db(unit.name, db)
        else:
            # Pre-warm the cache
            _graph.load_or_create(unit.name)
            logger.debug(f"Graph pre-loaded for {unit.name}")
