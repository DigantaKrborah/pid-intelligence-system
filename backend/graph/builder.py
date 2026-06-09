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

    def remove_document_nodes(self, unit_name: str, document_id: str) -> int:
        """Remove all graph nodes that came from a specific document. Returns count removed."""
        graph = self.load_or_create(unit_name)
        to_remove = [n for n, d in graph.nodes(data=True) if str(d.get("document_id", "")) == document_id]
        graph.remove_nodes_from(to_remove)
        self.save(unit_name)
        logger.info(f"Removed {len(to_remove)} nodes from unit {unit_name} (doc {document_id})")
        return len(to_remove)

    def get_nodes_by_document(self, unit_name: str, document_ids: list[str]) -> set[str]:
        """Return the set of tag names that belong to any of the given document IDs."""
        graph = self.load_or_create(unit_name)
        return {
            n for n, d in graph.nodes(data=True)
            if str(d.get("document_id", "")) in document_ids
        }

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

    def get_frontend_format(self, unit_name: str, include_cross_unit: bool = False) -> dict:
        """
        Returns graph as flat nodes/edges lists for streamlit-agraph.
        Merges cross-unit edges if requested.
        """
        graph = self.load_or_create(unit_name)
        nodes = [
            {"id": n, "label": n, **{k: v for k, v in d.items()}}
            for n, d in graph.nodes(data=True)
        ]
        edges = [
            {"source": u, "target": v, **{k: v2 for k, v2 in d.items()}}
            for u, v, d in graph.edges(data=True)
        ]

        if include_cross_unit:
            cross = self._load_cross_unit()
            cross_unit_name = unit_name.upper()
            # Add foreign nodes and cross-unit edges
            for n, d in cross.nodes(data=True):
                if d.get("unit") != cross_unit_name and n not in graph:
                    nodes.append({"id": n, "label": n, "cross_unit": True, **d})
            for u, v, d in cross.edges(data=True):
                src_unit = cross.nodes[u].get("unit", "")
                tgt_unit = cross.nodes[v].get("unit", "")
                if src_unit == cross_unit_name or tgt_unit == cross_unit_name:
                    edges.append({"source": u, "target": v, "cross_unit": True, **d})

        return {"nodes": nodes, "edges": edges}

    def get_impact_analysis(self, unit_name: str, tag: str, depth: int = 5) -> dict:
        """
        Returns all downstream equipment affected if `tag` is isolated/fails.
        Severity is based on downstream count.
        """
        graph = self.load_or_create(unit_name)
        if tag not in graph:
            return {"tag": tag, "found": False, "affected": [], "affected_count": 0, "severity": "unknown"}

        affected = list(nx.dfs_preorder_nodes(graph, tag, depth_limit=depth))[1:]

        affected_by_type: dict[str, list[str]] = {}
        for node in affected:
            node_type = graph.nodes[node].get("tag_type", "other")
            affected_by_type.setdefault(node_type, []).append(node)

        count = len(affected)
        severity = "high" if count > 10 else "medium" if count > 3 else "low"

        return {
            "tag": tag,
            "found": True,
            "affected": affected,
            "affected_count": count,
            "affected_by_type": affected_by_type,
            "severity": severity,
            "in_degree": graph.in_degree(tag),
            "out_degree": graph.out_degree(tag),
        }

    def rebuild_from_tags(self, unit_name: str, tags: list[dict], connections: list[dict]) -> None:
        """
        Rebuild a unit graph from raw data (e.g. after graph JSON is lost).
        tags: [{"tag", "tag_type", "description", ...}]
        connections: [{"source", "target", "connection_type", "line_number"}]
        """
        graph = nx.DiGraph(unit=unit_name)
        for t in tags:
            tag = t.pop("tag")
            graph.add_node(tag, unit=unit_name, **t)
        for c in connections:
            graph.add_edge(
                c["source"],
                c["target"],
                connection_type=c.get("connection_type", "pipeline"),
                line_number=c.get("line_number", ""),
            )
        self._graphs[unit_name] = graph
        self.save(unit_name)
        logger.info(f"Rebuilt graph for {unit_name}: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

    def get_cross_unit_graph_data(self) -> dict:
        """Returns the cross-unit graph in frontend format."""
        cross = self._load_cross_unit()
        nodes = [{"id": n, "label": n, **d} for n, d in cross.nodes(data=True)]
        edges = [{"source": u, "target": v, **d} for u, v, d in cross.edges(data=True)]
        return {"nodes": nodes, "edges": edges}

    def get_all_units_combined(self) -> dict:
        """Merge all loaded unit graphs + cross-unit connections into one view."""
        combined = nx.DiGraph()
        for unit_name, graph in self._graphs.items():
            for n, d in graph.nodes(data=True):
                combined.add_node(n, **d)
            for u, v, d in graph.edges(data=True):
                combined.add_edge(u, v, **d)
        cross = self._load_cross_unit()
        for n, d in cross.nodes(data=True):
            if n not in combined:
                combined.add_node(n, **d)
        for u, v, d in cross.edges(data=True):
            combined.add_edge(u, v, cross_unit=True, **d)
        nodes = [{"id": n, "label": n, **d} for n, d in combined.nodes(data=True)]
        edges = [{"source": u, "target": v, **d} for u, v, d in combined.edges(data=True)]
        return {"nodes": nodes, "edges": edges}

    def _load_cross_unit(self) -> nx.DiGraph:
        path = self._cross_unit_path()
        if path.exists():
            return nx.node_link_graph(json.loads(path.read_text()))
        return nx.DiGraph()

    def _save_cross_unit(self, graph: nx.DiGraph) -> None:
        self._cross_unit_path().write_text(json.dumps(nx.node_link_data(graph)))
