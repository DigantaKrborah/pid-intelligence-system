"""Core API route tests — no real DB/Ollama required (all external deps mocked)."""
import pytest
from unittest.mock import patch, MagicMock


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_has_required_keys(client):
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert "env"    in data
    assert "postgres" in data
    assert "ollama"   in data


def test_health_env_is_string(client):
    """env field is always a string — specific value depends on startup settings."""
    response = client.get("/health")
    assert isinstance(response.json()["env"], str)


def test_health_status_is_string(client):
    """Status is ok, degraded, or unreachable — all are valid string values."""
    status = client.get("/health").json()["status"]
    assert isinstance(status, str)
    assert status in ("ok", "degraded", "unreachable")


# ── Units ─────────────────────────────────────────────────────────────────────

def test_list_units_returns_200_with_empty_db(client, mock_db):
    """Units list returns 200 and empty list when DB has no units."""
    from unittest.mock import MagicMock
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    response = client.get("/api/v1/units/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_unit_conflict(client, mock_db, sample_unit):
    """POST /units returns 409 when unit already exists."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_unit
    mock_db.execute.return_value = mock_result

    response = client.post("/api/v1/units/", json={"name": "CDU"})
    assert response.status_code == 409


def test_get_unit_not_found(client, mock_db):
    """GET /units/{id} returns 404 for unknown unit."""
    import uuid
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/units/{fake_id}")
    assert response.status_code == 404


def test_archive_unit_not_found(client, mock_db):
    """DELETE /units/{id} returns 404 for unknown unit."""
    import uuid
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = client.delete(f"/api/v1/units/{uuid.uuid4()}")
    assert response.status_code == 404


# ── Graph ─────────────────────────────────────────────────────────────────────

def test_graph_returns_node_link_format(client):
    """GET /graph/{unit} returns node-link dict with nodes key."""
    response = client.get("/api/v1/graph/TESTUNIT")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    # NetworkX 3.3 uses "links", 3.4+ uses "edges" — accept either
    assert "links" in data or "edges" in data


def test_graph_frontend_format_has_edges(client):
    """GET /graph/{unit}/frontend uses 'edges' key for streamlit-agraph."""
    response = client.get("/api/v1/graph/TESTUNIT/frontend")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data        # frontend format uses "edges"


def test_graph_neighbours_unknown_tag(client):
    response = client.get("/api/v1/graph/CDU/neighbours/P-999")
    assert response.status_code == 200
    data = response.json()
    assert data["upstream"]   == []
    assert data["downstream"] == []


def test_graph_path_not_found(client):
    response = client.get("/api/v1/graph/CDU/path?source=P-999&target=V-999")
    assert response.status_code == 200
    assert response.json()["found"] is False


def test_graph_stats_returns_counts(client):
    response = client.get("/api/v1/graph/CDU/stats")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data


def test_graph_impact_unknown_tag_returns_404(client):
    response = client.get("/api/v1/graph/CDU/impact/UNKNOWN-999")
    assert response.status_code == 404


# ── NL Query ─────────────────────────────────────────────────────────────────

def test_nl_query_without_unit_id_returns_message(client):
    response = client.post("/api/v1/query/nl", json={"question": "List all pumps"})
    assert response.status_code == 200
    assert "select a unit" in response.json()["answer"].lower()


def test_nl_query_unknown_unit_returns_404(client, mock_db):
    """NL query with unknown unit_id returns 404."""
    import uuid
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = client.post("/api/v1/query/nl", json={
        "question":  "List all pumps",
        "unit_id":   str(uuid.uuid4()),
    })
    assert response.status_code == 404


# ── Search ────────────────────────────────────────────────────────────────────

def test_search_tags_requires_q(client):
    response = client.get("/api/v1/search/tags")
    assert response.status_code == 422


def test_search_tags_empty_returns_200(client, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    response = client.get("/api/v1/search/tags?q=NONEXISTENT")
    assert response.status_code == 200
    assert response.json() == []


def test_search_tag_not_found(client, mock_db):
    mock_db.execute.return_value.first.return_value = None
    response = client.get("/api/v1/search/tags/UNKNOWN-999")
    assert response.status_code == 404


def test_list_documents_returns_200(client, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    response = client.get("/api/v1/search/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ── Upload ────────────────────────────────────────────────────────────────────

def test_upload_pid_validates_pdf_type(client, mock_db, sample_unit):
    """Non-PDF file is rejected with 400."""
    mock_db.execute.return_value.scalar_one_or_none.return_value = sample_unit
    import uuid
    response = client.post(
        "/api/v1/upload/pid",
        data={"unit_id": str(uuid.uuid4())},
        files={"files": ("diagram.xlsx", b"fake-excel", "application/vnd.ms-excel")},
    )
    assert response.status_code == 400


def test_upload_document_validates_type(client, mock_db, sample_unit):
    """Non-PDF/DOCX file rejected with 400."""
    mock_db.execute.return_value.scalar_one_or_none.return_value = sample_unit
    import uuid
    response = client.post(
        "/api/v1/upload/document",
        data={"unit_id": str(uuid.uuid4()), "doc_type": "SOP"},
        files={"file": ("manual.txt", b"text content", "text/plain")},
    )
    assert response.status_code == 400


# ── Incidents ─────────────────────────────────────────────────────────────────

def test_list_incidents_returns_200_empty(client, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    response = client.get("/api/v1/incidents/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_incident_not_found(client, mock_db):
    import uuid
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = client.get(f"/api/v1/incidents/{uuid.uuid4()}")
    assert response.status_code == 404
