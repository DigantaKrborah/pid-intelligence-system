import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_units_returns_501(client):
    """Units endpoint returns 501 until implemented."""
    response = client.get("/api/v1/units/")
    assert response.status_code == 501


def test_graph_endpoint_returns_empty_graph(client):
    """Graph endpoint returns node-link dict for unknown unit (empty graph)."""
    response = client.get("/api/v1/graph/TESTUNIT")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "links" in data


def test_graph_neighbours_unknown_tag(client):
    response = client.get("/api/v1/graph/CDU/neighbours/P-999")
    assert response.status_code == 200
    data = response.json()
    assert data["upstream"] == []
    assert data["downstream"] == []


def test_graph_path_not_found(client):
    response = client.get("/api/v1/graph/CDU/path?source=P-999&target=V-999")
    assert response.status_code == 200
    assert response.json()["found"] is False


def test_nl_query_without_unit_returns_error_message(client):
    response = client.post("/api/v1/query/nl", json={"question": "List all pumps"})
    assert response.status_code == 200
    assert "select a unit" in response.json()["answer"].lower()
