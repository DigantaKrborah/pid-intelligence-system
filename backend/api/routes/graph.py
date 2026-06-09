from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from backend.graph.builder import GraphBuilder
from backend.services.graph_service import get_graph_builder as _get_graph_builder

router = APIRouter()


class CrossUnitConnectionRequest(BaseModel):
    source_tag: str
    source_unit: str
    target_tag: str
    target_unit: str
    connection_type: str = "pipeline"


@router.get("/{unit_name}")
async def get_unit_graph(unit_name: str):
    """Return full graph data for a unit (node-link format for frontend rendering)."""
    return _get_graph_builder().get_graph_data(unit_name)


@router.get("/{unit_name}/stats")
async def get_graph_stats(unit_name: str):
    """Return graph statistics for a unit."""
    return _get_graph_builder().get_graph_stats(unit_name)


@router.get("/{unit_name}/neighbours/{tag}")
async def get_neighbours(unit_name: str, tag: str, depth: int = Query(1, ge=1, le=5)):
    """Get upstream and downstream neighbours of a tag."""
    return _get_graph_builder().get_neighbours(unit_name, tag, depth)


@router.get("/{unit_name}/path")
async def get_path(unit_name: str, source: str = Query(...), target: str = Query(...)):
    """Find shortest process path between two tags."""
    path = _get_graph_builder().find_path(unit_name, source, target)
    if path is None:
        return {"found": False, "path": []}
    return {"found": True, "path": path, "length": len(path) - 1}


@router.get("/{unit_name}/frontend")
async def get_frontend_graph(
    unit_name: str,
    include_cross_unit: bool = Query(False),
):
    """Graph as flat nodes/edges lists ready for streamlit-agraph rendering."""
    return _get_graph_builder().get_frontend_format(unit_name, include_cross_unit=include_cross_unit)


@router.get("/{unit_name}/impact/{tag}")
async def get_impact_analysis(
    unit_name: str,
    tag: str,
    depth: int = Query(5, ge=1, le=10),
):
    """Return all downstream equipment affected if a tag is isolated or fails."""
    result = _get_graph_builder().get_impact_analysis(unit_name, tag, depth)
    if not result["found"]:
        raise HTTPException(status_code=404, detail=f"Tag '{tag}' not found in unit '{unit_name}'")
    return result


@router.get("/{unit_name}/by-type/{tag_type}")
async def get_by_type(unit_name: str, tag_type: str):
    """List all equipment of a given type in a unit."""
    items = _get_graph_builder().get_nodes_by_type(unit_name, tag_type)
    return {"unit": unit_name, "tag_type": tag_type, "count": len(items), "items": items}


@router.get("/cross-unit/graph")
async def get_cross_unit_graph():
    """Return the cross-unit connection graph for all units."""
    return _get_graph_builder().get_cross_unit_graph_data()


@router.get("/cross-unit/all")
async def get_all_units_graph():
    """Merge all loaded unit graphs and cross-unit connections into one view."""
    return _get_graph_builder().get_all_units_combined()


@router.post("/cross-unit/connect", status_code=201)
async def add_cross_unit_connection(payload: CrossUnitConnectionRequest):
    """Manually register a cross-unit piping connection."""
    _get_graph_builder().add_cross_unit_connection(
        source_tag=payload.source_tag,
        source_unit=payload.source_unit,
        target_tag=payload.target_tag,
        target_unit=payload.target_unit,
        connection_type=payload.connection_type,
    )
    return {
        "source": f"{payload.source_unit}/{payload.source_tag}",
        "target": f"{payload.target_unit}/{payload.target_tag}",
        "connection_type": payload.connection_type,
        "status": "created",
    }
