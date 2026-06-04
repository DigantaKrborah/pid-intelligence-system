"""
Integration tests for the units API.
Requires: docker compose up (postgres, backend).

Run with:
    pytest tests/integration/ -m integration

These tests are excluded from the default CI run (which only runs unit tests).
"""
import pytest
import httpx

BASE_URL = "http://localhost:8000"


@pytest.mark.integration
class TestUnitsIntegration:

    def test_health_ok(self):
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        assert r.status_code == 200
        assert r.json()["postgres"] == "ok"

    def test_create_and_list_unit(self):
        # Create
        r = httpx.post(f"{BASE_URL}/api/v1/units/", json={"name": "TEST_CDU_INT", "description": "Integration test unit"}, timeout=5)
        assert r.status_code == 201
        unit = r.json()
        assert unit["name"] == "TEST_CDU_INT"
        unit_id = unit["id"]

        # List includes new unit
        r2 = httpx.get(f"{BASE_URL}/api/v1/units/", timeout=5)
        assert r2.status_code == 200
        names = [u["name"] for u in r2.json()]
        assert "TEST_CDU_INT" in names

        # Cleanup — archive
        r3 = httpx.delete(f"{BASE_URL}/api/v1/units/{unit_id}", timeout=5)
        assert r3.status_code == 204

    def test_create_duplicate_unit_returns_409(self):
        httpx.post(f"{BASE_URL}/api/v1/units/", json={"name": "DUP_INT_TEST"}, timeout=5)
        r2 = httpx.post(f"{BASE_URL}/api/v1/units/", json={"name": "DUP_INT_TEST"}, timeout=5)
        assert r2.status_code == 409
        # Cleanup
        units = httpx.get(f"{BASE_URL}/api/v1/units/", timeout=5).json()
        for u in units:
            if u["name"] == "DUP_INT_TEST":
                httpx.delete(f"{BASE_URL}/api/v1/units/{u['id']}", timeout=5)

    def test_get_unit_stats(self):
        r = httpx.post(f"{BASE_URL}/api/v1/units/", json={"name": "STATS_INT_TEST"}, timeout=5)
        unit_id = r.json()["id"]

        r2 = httpx.get(f"{BASE_URL}/api/v1/units/{unit_id}", timeout=5)
        assert r2.status_code == 200
        stats = r2.json()
        assert "total_tags"       in stats
        assert "total_documents"  in stats
        assert "graph_node_count" in stats

        httpx.delete(f"{BASE_URL}/api/v1/units/{unit_id}", timeout=5)

    def test_get_nonexistent_unit_returns_404(self):
        import uuid
        r = httpx.get(f"{BASE_URL}/api/v1/units/{uuid.uuid4()}", timeout=5)
        assert r.status_code == 404
