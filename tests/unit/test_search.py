import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_tag():
    tag = MagicMock()
    tag.id = uuid.uuid4()
    tag.unit_id = uuid.uuid4()
    tag.tag = "P-101"
    tag.tag_type = "pump"
    tag.description = "Feed pump"
    tag.page_number = 3
    tag.confidence = 0.95
    tag.raw_attributes = {"line_number": "4-CS-001"}
    tag.document_id = uuid.uuid4()
    return tag


def test_search_tags_returns_empty_list(client):
    """Search with no matching results returns empty list, not 500."""
    response = client.get("/api/v1/search/tags?q=NONEXISTENT_TAG_XYZ")
    assert response.status_code == 200
    assert response.json() == []


def test_search_tags_requires_query(client):
    """q param is required — missing it should return 422."""
    response = client.get("/api/v1/search/tags")
    assert response.status_code == 422


def test_get_tag_not_found(client):
    """Unknown tag returns 404."""
    response = client.get("/api/v1/search/tags/UNKNOWN-999")
    assert response.status_code == 404


def test_graph_impact_endpoint_unknown_tag(client):
    """Impact analysis on unknown tag returns 404."""
    response = client.get("/api/v1/graph/CDU/impact/UNKNOWN-999")
    assert response.status_code == 404


def test_graph_impact_endpoint_known_tag(client):
    """Impact analysis on known tag returns impact dict."""
    with patch("backend.api.routes.graph._graph") as mock_graph:
        mock_graph.get_impact_analysis.return_value = {
            "tag": "P-101",
            "found": True,
            "affected": ["V-101"],
            "affected_count": 1,
            "affected_by_type": {"vessel": ["V-101"]},
            "severity": "low",
            "in_degree": 0,
            "out_degree": 1,
        }
        response = client.get("/api/v1/graph/CDU/impact/P-101")
    assert response.status_code == 200
    data = response.json()
    assert data["tag"] == "P-101"
    assert data["severity"] == "low"
    assert "V-101" in data["affected"]


def test_graph_frontend_format_endpoint(client):
    """Frontend format endpoint returns nodes and edges keys."""
    with patch("backend.api.routes.graph._graph") as mock_graph:
        mock_graph.get_frontend_format.return_value = {
            "nodes": [{"id": "P-101", "label": "P-101", "tag_type": "pump"}],
            "edges": [],
        }
        response = client.get("/api/v1/graph/CDU/frontend")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data


def test_add_cross_unit_connection(client):
    """POST to cross-unit/connect creates the connection."""
    with patch("backend.api.routes.graph._graph") as mock_graph:
        mock_graph.add_cross_unit_connection.return_value = None
        response = client.post("/api/v1/graph/cross-unit/connect", json={
            "source_tag": "P-101",
            "source_unit": "CDU",
            "target_tag": "V-201",
            "target_unit": "VDU",
            "connection_type": "pipeline",
        })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "created"
    assert "CDU/P-101" in data["source"]
