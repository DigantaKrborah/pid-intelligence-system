import json
import os
from pathlib import Path
from typing import Optional
import networkx as nx
from loguru import logger

from backend.config import get_settings


class GraphBuilder:
    """Builds and persists NetworkX graphs per unit + cross-unit graph."""

    def __init__(self):
        self.settings = get_settings()
        self.graph_dir = Path(self.settings.graph_dir)
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        self._graphs: dict[str, nx.DiGraph] = {}

    def _graph_path(self, unit_name: str) -> Path:
        return self.graph_dir / f"{unit_name.lower()}_graph.json"

    def _cross_unit_path(self) -> Path:
        return self.graph_dir / "cross_unit_graph.json"

    def load_or_create(self, unit_name: str) -> nx.DiGraph:
        if unit_name in self._graphs:
            return self._graphs[unit_name]
        path = self._graph_path(unit_name)
        if path.exists():
            graph = nx.node_link_graph(json.loads(path.read_text()))
        else:
            graph = nx.DiGraph(unit=unit_name)
        self._graphs[unit_name] = graph
        return graph

    def save(self, unit_name: str) -> None:
        graph = self._graphs.get(unit_name)
        if graph is None:
            return
        path = self._graph_path(unit_name)
        path.write_text(json.dumps(nx.node_link_data(graph)))
        logger.debug(f"Graph saved for unit {unit_name}: {graph.number_of_nodes()} nodes")

    def add_equipment(self, unit_name: str, tag: str, tag_type: str, **attrs) -> None:
        graph = self.load_or_create(unit_name)
        graph.add_node(tag, unit=unit_name, tag_type=tag_type, **attrs)

    def add_connection(
        self, unit_name: str, source: str, target: str, connection_type: str = "pipeline", **attrs
    ) -> None:
        graph = self.load_or_create(unit_name)
        graph.add_edge(source, target, connection_type=connection_type, **attrs)

    def add_cross_unit_connection(
        self,
        source_tag: str,
        source_unit: str,
        target_tag: str,
        target_unit: str,
        connection_type: str = "pipeline",
    ) -> None:
        cross = self._load_cross_unit()
        cross.add_node(source_tag, unit=source_unit)
        cross.add_node(target_tag, unit=target_unit)
        cross.add_edge(source_tag, target_tag, connection_type=connection_type)
        self._save_cross_unit(cross)

    def get_neighbours(self, unit_name: str, tag: str, depth: int = 1) -> dict:
        graph = self.load_or_create(unit_name)
        if tag not in graph:
            return {"upstream": [], "downstream": []}
        downstream = list(nx.dfs_preorder_nodes(graph, tag, depth_limit=depth))[1:]
        upstream = list(nx.dfs_preorder_nodes(graph.reverse(), tag, depth_limit=depth))[1:]
        return {"upstream": upstream, "downstream": downstream}

    def find_path(self, unit_name: str, source: str, target: str) -> Optional[list[str]]:
        graph = self.load_or_create(unit_name)
        try:
            return nx.shortest_path(graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_nodes_by_type(self, unit_name: str, tag_type: str) -> list[dict]:
        graph = self.load_or_create(unit_name)
        return [
            {"tag": n, **d}
            for n, d in graph.nodes(data=True)
            if d.get("tag_type") == tag_type
        ]

    def get_graph_stats(self, unit_name: str) -> dict:
        graph = self.load_or_create(unit_name)
        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "is_dag": nx.is_directed_acyclic_graph(graph),
        }

    def get_graph_data(self, unit_name: str) -> dict:
        """Returns node-link format suitable for frontend graph rendering."""
        graph = self.load_or_create(unit_name)
        return nx.node_link_data(graph)

    def _load_cross_unit(self) -> nx.DiGraph:
        path = self._cross_unit_path()
        if path.exists():
            return nx.node_link_graph(json.loads(path.read_text()))
        return nx.DiGraph()

    def _save_cross_unit(self, graph: nx.DiGraph) -> None:
        self._cross_unit_path().write_text(json.dumps(nx.node_link_data(graph)))
