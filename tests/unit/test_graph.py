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
