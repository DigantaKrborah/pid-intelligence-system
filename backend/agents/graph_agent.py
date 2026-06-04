"""
Graph Agent — specialist for all graph-based engineering queries.
Called as tools by the CoordinatorAgent.
"""
from backend.graph.builder import GraphBuilder


class GraphAgent:
    def __init__(self, graph: GraphBuilder, unit_name: str):
        self.graph = graph
        self.unit_name = unit_name

    def search_equipment(self, tag: str) -> dict:
        """Return details and connections for a specific tag."""
        neighbours = self.graph.get_neighbours(self.unit_name, tag, depth=1)
        graph = self.graph.load_or_create(self.unit_name)
        attrs = dict(graph.nodes.get(tag, {})) if tag in graph else {}
        return {
            "tag": tag,
            "found": tag in graph,
            "tag_type": attrs.get("tag_type", "unknown"),
            "description": attrs.get("description", ""),
            "upstream": neighbours["upstream"],
            "downstream": neighbours["downstream"],
            "unit": self.unit_name,
        }

    def list_by_type(self, equipment_type: str) -> dict:
        """List all equipment of a given type in the unit."""
        items = self.graph.get_nodes_by_type(self.unit_name, equipment_type)
        return {
            "equipment_type": equipment_type,
            "unit": self.unit_name,
            "count": len(items),
            "tags": [i["tag"] for i in items],
        }

    def trace_path(self, source_tag: str, target_tag: str) -> dict:
        """Find the shortest process path between two tags."""
        path = self.graph.find_path(self.unit_name, source_tag, target_tag)
        return {
            "source": source_tag,
            "target": target_tag,
            "found": path is not None,
            "path": path or [],
            "length": len(path) - 1 if path else 0,
            "unit": self.unit_name,
        }

    def analyze_impact(self, tag: str, depth: int = 5) -> dict:
        """Return downstream impact analysis when a tag fails or is isolated."""
        return self.graph.get_impact_analysis(self.unit_name, tag, depth)

    def get_all_tags(self) -> dict:
        """Return summary stats and tag list for the unit graph."""
        stats = self.graph.get_graph_stats(self.unit_name)
        graph = self.graph.load_or_create(self.unit_name)
        tag_list = [
            {"tag": n, "type": d.get("tag_type", "other")}
            for n, d in graph.nodes(data=True)
        ]
        return {"unit": self.unit_name, "stats": stats, "tags": tag_list[:200]}
