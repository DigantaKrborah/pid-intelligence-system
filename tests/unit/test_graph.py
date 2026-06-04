import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from backend.graph.builder import GraphBuilder


@pytest.fixture
def graph_builder(tmp_path):
    with patch("backend.graph.builder.get_settings") as mock:
        mock.return_value.graph_dir = str(tmp_path)
        builder = GraphBuilder()
        yield builder


def test_add_and_retrieve_equipment(graph_builder):
    graph_builder.add_equipment("CDU", "P-101", "pump", description="Feed pump")
    graph = graph_builder.load_or_create("CDU")
    assert "P-101" in graph.nodes
    assert graph.nodes["P-101"]["tag_type"] == "pump"


def test_add_connection_and_get_neighbours(graph_builder):
    graph_builder.add_equipment("CDU", "P-101", "pump")
    graph_builder.add_equipment("CDU", "V-101", "vessel")
    graph_builder.add_connection("CDU", "P-101", "V-101", "pipeline")

    neighbours = graph_builder.get_neighbours("CDU", "P-101")
    assert "V-101" in neighbours["downstream"]
    assert neighbours["upstream"] == []


def test_find_path_exists(graph_builder):
    for tag, typ in [("P-101", "pump"), ("E-101", "exchanger"), ("T-101", "vessel")]:
        graph_builder.add_equipment("CDU", tag, typ)
    graph_builder.add_connection("CDU", "P-101", "E-101")
    graph_builder.add_connection("CDU", "E-101", "T-101")

    path = graph_builder.find_path("CDU", "P-101", "T-101")
    assert path == ["P-101", "E-101", "T-101"]


def test_find_path_not_found(graph_builder):
    graph_builder.add_equipment("CDU", "P-101", "pump")
    graph_builder.add_equipment("CDU", "V-999", "vessel")
    path = graph_builder.find_path("CDU", "P-101", "V-999")
    assert path is None


def test_get_nodes_by_type(graph_builder, sample_extracted_tags):
    for t in sample_extracted_tags:
        graph_builder.add_equipment("CDU", t["tag"], t["tag_type"])

    pumps = graph_builder.get_nodes_by_type("CDU", "pump")
    assert len(pumps) == 1
    assert pumps[0]["tag"] == "P-101"


def test_graph_persists_and_reloads(graph_builder):
    graph_builder.add_equipment("CDU", "P-101", "pump")
    graph_builder.save("CDU")

    # Create new builder pointing at same dir
    with patch("backend.graph.builder.get_settings") as mock:
        mock.return_value.graph_dir = graph_builder.settings.graph_dir
        new_builder = GraphBuilder()
        graph = new_builder.load_or_create("CDU")
        assert "P-101" in graph.nodes


def test_graph_stats(graph_builder):
    graph_builder.add_equipment("CDU", "P-101", "pump")
    graph_builder.add_equipment("CDU", "V-101", "vessel")
    graph_builder.add_connection("CDU", "P-101", "V-101")

    stats = graph_builder.get_graph_stats("CDU")
    assert stats["nodes"] == 2
    assert stats["edges"] == 1


def test_cross_unit_connection(graph_builder):
    graph_builder.add_equipment("CDU", "P-101", "pump")
    graph_builder.add_equipment("VDU", "V-201", "vessel")
    graph_builder.add_cross_unit_connection("P-101", "CDU", "V-201", "VDU")

    cross = graph_builder._load_cross_unit()
    assert "P-101" in cross.nodes
    assert "V-201" in cross.nodes
    assert cross.has_edge("P-101", "V-201")


# ── Impact analysis ────────────────────────────────────────────────────────────

def test_impact_analysis_returns_downstream(graph_builder):
    for tag, typ in [("P-101", "pump"), ("E-101", "exchanger"), ("T-101", "vessel"), ("P-201", "pump")]:
        graph_builder.add_equipment("CDU", tag, typ)
    graph_builder.add_connection("CDU", "P-101", "E-101")
    graph_builder.add_connection("CDU", "E-101", "T-101")
    graph_builder.add_connection("CDU", "T-101", "P-201")

    result = graph_builder.get_impact_analysis("CDU", "P-101")
    assert result["found"] is True
    assert "E-101" in result["affected"]
    assert "T-101" in result["affected"]
    assert "P-201" in result["affected"]
    assert result["affected_count"] == 3


def test_impact_analysis_unknown_tag(graph_builder):
    result = graph_builder.get_impact_analysis("CDU", "UNKNOWN-999")
    assert result["found"] is False
    assert result["affected"] == []
    assert result["severity"] == "unknown"


def test_impact_analysis_severity_low(graph_builder):
    graph_builder.add_equipment("CDU", "P-101", "pump")
    graph_builder.add_equipment("CDU", "V-101", "vessel")
    graph_builder.add_connection("CDU", "P-101", "V-101")
    result = graph_builder.get_impact_analysis("CDU", "P-101")
    assert result["severity"] == "low"
    assert result["affected_count"] == 1


def test_impact_analysis_groups_by_type(graph_builder):
    graph_builder.add_equipment("CDU", "P-101", "pump")
    graph_builder.add_equipment("CDU", "P-102", "pump")
    graph_builder.add_equipment("CDU", "V-101", "vessel")
    graph_builder.add_connection("CDU", "P-101", "P-102")
    graph_builder.add_connection("CDU", "P-101", "V-101")
    result = graph_builder.get_impact_analysis("CDU", "P-101")
    assert "pump" in result["affected_by_type"]
    assert "vessel" in result["affected_by_type"]


# ── Frontend format ────────────────────────────────────────────────────────────

def test_get_frontend_format_structure(graph_builder):
    graph_builder.add_equipment("CDU", "P-101", "pump")
    graph_builder.add_equipment("CDU", "V-101", "vessel")
    graph_builder.add_connection("CDU", "P-101", "V-101")

    data = graph_builder.get_frontend_format("CDU")
    assert "nodes" in data
    assert "edges" in data
    node_ids = [n["id"] for n in data["nodes"]]
    assert "P-101" in node_ids
    assert "V-101" in node_ids
    assert len(data["edges"]) == 1
    assert data["edges"][0]["source"] == "P-101"
    assert data["edges"][0]["target"] == "V-101"


# ── Rebuild from tags ──────────────────────────────────────────────────────────

def test_rebuild_from_tags(graph_builder):
    tags = [
        {"tag": "P-101", "tag_type": "pump", "description": "Feed pump"},
        {"tag": "V-101", "tag_type": "vessel", "description": "Feed drum"},
    ]
    connections = [
        {"source": "P-101", "target": "V-101", "connection_type": "pipeline", "line_number": "4-CS-001"},
    ]
    graph_builder.rebuild_from_tags("CDU", tags, connections)

    graph = graph_builder.load_or_create("CDU")
    assert "P-101" in graph.nodes
    assert "V-101" in graph.nodes
    assert graph.has_edge("P-101", "V-101")


# ── Cross-unit combined view ───────────────────────────────────────────────────

def test_get_all_units_combined(graph_builder):
    graph_builder.add_equipment("CDU", "P-101", "pump")
    graph_builder.add_equipment("VDU", "V-201", "vessel")
    graph_builder.add_cross_unit_connection("P-101", "CDU", "V-201", "VDU")

    combined = graph_builder.get_all_units_combined()
    node_ids = [n["id"] for n in combined["nodes"]]
    assert "P-101" in node_ids
    assert "V-201" in node_ids
    cross_edges = [e for e in combined["edges"] if e.get("cross_unit")]
    assert len(cross_edges) == 1
