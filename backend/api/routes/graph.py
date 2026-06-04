from fastapi import APIRouter, Query
from uuid import UUID
from typing import Optional
from backend.graph.builder import GraphBuilder

router = APIRouter()
_graph = GraphBuilder()


@router.get("/{unit_name}")
async def get_unit_graph(unit_name: str):
    """Return full graph data for a unit (node-link format for frontend rendering)."""
    return _graph.get_graph_data(unit_name)


@router.get("/{unit_name}/stats")
async def get_graph_stats(unit_name: str):
    """Return graph statistics for a unit."""
    return _graph.get_graph_stats(unit_name)


@router.get("/{unit_name}/neighbours/{tag}")
async def get_neighbours(unit_name: str, tag: str, depth: int = Query(1, ge=1, le=5)):
    """Get upstream and downstream neighbours of a tag."""
    return _graph.get_neighbours(unit_name, tag, depth)


@router.get("/{unit_name}/path")
async def get_path(unit_name: str, source: str = Query(...), target: str = Query(...)):
    """Find shortest process path between two tags."""
    path = _graph.find_path(unit_name, source, target)
    if path is None:
        return {"found": False, "path": []}
    return {"found": True, "path": path, "length": len(path) - 1}
