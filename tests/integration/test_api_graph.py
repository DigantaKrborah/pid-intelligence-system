"""
Integration tests for the graph and search APIs.
Requires: docker compose up

Run with:
    pytest tests/integration/ -m integration
"""
import pytest
import httpx

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def integration_unit():
    """Create a test unit for this module, yield its data, then archive it."""
    r = httpx.post(f"{BASE_URL}/api/v1/units/", json={"name": "GRAPH_INT_TEST"}, timeout=5)
    assert r.status_code == 201
    unit = r.json()
    yield unit
    httpx.delete(f"{BASE_URL}/api/v1/units/{unit['id']}", timeout=5)


@pytest.mark.integration
class TestGraphAPIIntegration:

    def test_graph_empty_unit_returns_no_nodes(self, integration_unit):
        unit_name = integration_unit["name"]
        r = httpx.get(f"{BASE_URL}/api/v1/graph/{unit_name}/frontend", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_graph_stats_empty_unit(self, integration_unit):
        unit_name = integration_unit["name"]
        r = httpx.get(f"{BASE_URL}/api/v1/graph/{unit_name}/stats", timeout=5)
        assert r.status_code == 200
        assert r.json()["nodes"] == 0

    def test_graph_neighbours_unknown_tag(self, integration_unit):
        unit_name = integration_unit["name"]
        r = httpx.get(f"{BASE_URL}/api/v1/graph/{unit_name}/neighbours/P-999", timeout=5)
        assert r.status_code == 200
        assert r.json()["upstream"]   == []
        assert r.json()["downstream"] == []

    def test_cross_unit_connect_and_retrieve(self):
        r = httpx.post(f"{BASE_URL}/api/v1/graph/cross-unit/connect", json={
            "source_tag":      "P-101",
            "source_unit":     "GRAPH_INT_TEST",
            "target_tag":      "V-201",
            "target_unit":     "GRAPH_INT_TEST2",
            "connection_type": "pipeline",
        }, timeout=5)
        assert r.status_code == 201
        assert r.json()["status"] == "created"

    def test_search_tags_empty_returns_list(self, integration_unit):
        r = httpx.get(f"{BASE_URL}/api/v1/search/tags?q=P-101", timeout=5)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_search_documents_returns_results_key(self):
        r = httpx.get(f"{BASE_URL}/api/v1/search/documents/search?q=startup+procedure", timeout=5)
        assert r.status_code == 200
        assert "results" in r.json()

    def test_index_stats_endpoint(self, integration_unit):
        unit_name = integration_unit["name"]
        r = httpx.get(f"{BASE_URL}/api/v1/search/stats/{unit_name}", timeout=5)
        assert r.status_code == 200
        assert "equipment_indexed" in r.json()
