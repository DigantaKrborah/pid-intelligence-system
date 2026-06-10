"""Centralised API client for all frontend → backend calls."""
import os
from typing import Optional
import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 10


# ── Low-level helpers ──────────────────────────────────────────────────────────

def _get(path: str, params: dict | None = None) -> tuple[int, any]:
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", params=params, timeout=TIMEOUT)
        return r.status_code, r.json()
    except Exception as exc:
        return 0, {"error": str(exc)}


def _post(path: str, json: dict | None = None, data: dict | None = None,
          files: dict | None = None, timeout: int = 30) -> tuple[int, any]:
    try:
        r = httpx.post(f"{BACKEND_URL}{path}", json=json, data=data,
                       files=files, timeout=timeout)
        return r.status_code, r.json()
    except Exception as exc:
        return 0, {"error": str(exc)}


def _patch(path: str, json: dict | None = None) -> tuple[int, any]:
    try:
        r = httpx.patch(f"{BACKEND_URL}{path}", json=json, timeout=TIMEOUT)
        return r.status_code, r.json()
    except Exception as exc:
        return 0, {"error": str(exc)}


def _delete(path: str) -> tuple[int, any]:
    try:
        r = httpx.delete(f"{BACKEND_URL}{path}", timeout=TIMEOUT)
        return r.status_code, r.json()
    except Exception as exc:
        return 0, {"error": str(exc)}


# ── Units ──────────────────────────────────────────────────────────────────────

def get_units() -> list[dict]:
    status, data = _get("/api/v1/units/")
    return data if status == 200 else []


def create_unit(name: str, description: str = "") -> tuple[bool, str]:
    status, data = _post("/api/v1/units/", json={"name": name, "description": description})
    if status == 201:
        return True, data.get("id", "")
    msg = data.get("detail", data.get("error", "Unknown error"))
    return False, msg


def get_unit_stats(unit_id: str) -> dict:
    status, data = _get(f"/api/v1/units/{unit_id}")
    return data if status == 200 else {}


# ── Session state helpers ──────────────────────────────────────────────────────

def get_selected_unit() -> dict | None:
    """Returns {name, id} for the currently selected unit, or None."""
    return st.session_state.get("selected_unit_obj")


def set_selected_unit(unit: dict) -> None:
    """Persist unit {name, id} to session state."""
    st.session_state["selected_unit_obj"] = unit
    st.session_state["selected_unit"] = unit["name"]
    st.session_state["selected_unit_id"] = unit["id"]


def require_unit() -> dict:
    """
    Call at the top of any page that needs a unit.
    Stops the page with a warning if no unit is selected.
    """
    unit = get_selected_unit()
    if not unit:
        st.warning("👈 Please select a process unit from the sidebar first.")
        st.stop()
    return unit


# ── Upload ────────────────────────────────────────────────────────────────────

def list_recent_uploads(unit_id: str, limit: int = 5) -> list[dict]:
    """Return the most recent P&ID documents for a unit (for dashboard)."""
    status, data = _get(f"/api/v1/upload/recent/{unit_id}", {"limit": limit})
    return data if status == 200 and isinstance(data, list) else []


def upload_pid_files(unit_id: str, files: list) -> list[dict]:
    """Upload multiple PDF files. Returns list of result dicts per file."""
    results = []
    for f in files:
        status, data = _post(
            "/api/v1/upload/pid",
            data={"unit_id": unit_id},
            files={"files": (f.name, f.getvalue(), "application/pdf")},
            timeout=60,
        )
        results.append({"filename": f.name, "status": status, "data": data})
    return results


def get_upload_status(document_id: str) -> dict:
    status, data = _get(f"/api/v1/upload/status/{document_id}")
    return data if status == 200 else {}


def list_all_documents(unit_id: str) -> list[dict]:
    status, data = _get(f"/api/v1/upload/list/{unit_id}")
    return data if status == 200 else []


def delete_document(document_id: str) -> tuple[bool, str]:
    status, data = _delete(f"/api/v1/upload/pid/{document_id}")
    if status == 200:
        return True, data.get("filename", "")
    return False, data.get("detail", data.get("error", "Delete failed"))


def list_unit_tags(unit_id: str, document_id: str | None = None) -> list[dict]:
    params = {"document_id": document_id} if document_id else {}
    status, data = _get(f"/api/v1/tags/list/{unit_id}", params)
    return data if status == 200 and isinstance(data, list) else []


def patch_tag(tag_id: str, tag_type: str | None = None, description: str | None = None) -> bool:
    body: dict = {}
    if tag_type is not None:
        body["tag_type"] = tag_type
    if description is not None:
        body["description"] = description
    status, _ = _patch(f"/api/v1/tags/{tag_id}", json=body)
    return status == 200


def upload_document(unit_id: str, doc_type: str, file) -> tuple[bool, dict]:
    status, data = _post(
        "/api/v1/upload/document",
        data={"unit_id": unit_id, "doc_type": doc_type},
        files={"file": (file.name, file.getvalue(), "application/octet-stream")},
    )
    return status == 200, data


# ── Search ────────────────────────────────────────────────────────────────────

def search_tags(q: str, unit_id: str | None = None, tag_type: str | None = None,
                limit: int = 20, semantic: bool = False) -> list[dict]:
    params: dict = {"q": q, "limit": limit, "semantic": semantic}
    if unit_id:
        params["unit_id"] = unit_id
    if tag_type:
        params["tag_type"] = tag_type
    status, data = _get("/api/v1/search/tags", params)
    return data if status == 200 else []


def get_tag_detail(tag: str, unit_id: str | None = None) -> dict | None:
    params = {"unit_id": unit_id} if unit_id else {}
    status, data = _get(f"/api/v1/search/tags/{tag}", params)
    return data if status == 200 else None


def list_documents(unit_id: str | None = None) -> list[dict]:
    params = {"unit_id": unit_id} if unit_id else {}
    status, data = _get("/api/v1/search/documents", params)
    return data if status == 200 else []


def search_documents(q: str, unit_id: str | None = None) -> list[dict]:
    params: dict = {"q": q}
    if unit_id:
        params["unit_id"] = unit_id
    status, data = _get("/api/v1/search/documents/search", params)
    return data.get("results", []) if status == 200 else []


# ── Graph ─────────────────────────────────────────────────────────────────────

def get_graph(unit_name: str, include_cross_unit: bool = False) -> dict:
    params = {"include_cross_unit": str(include_cross_unit).lower()}
    status, data = _get(f"/api/v1/graph/{unit_name}/frontend", params)
    return data if status == 200 else {"nodes": [], "edges": []}


def get_graph_stats(unit_name: str) -> dict:
    status, data = _get(f"/api/v1/graph/{unit_name}/stats")
    return data if status == 200 else {"nodes": 0, "edges": 0}


def get_neighbours(unit_name: str, tag: str, depth: int = 1) -> dict:
    status, data = _get(f"/api/v1/graph/{unit_name}/neighbours/{tag}", {"depth": depth})
    return data if status == 200 else {"upstream": [], "downstream": []}


def get_impact(unit_name: str, tag: str) -> dict | None:
    status, data = _get(f"/api/v1/graph/{unit_name}/impact/{tag}")
    return data if status == 200 else None


def get_path(unit_name: str, source: str, target: str) -> dict:
    status, data = _get(f"/api/v1/graph/{unit_name}/path", {"source": source, "target": target})
    return data if status == 200 else {"found": False, "path": []}


# ── NL Query ─────────────────────────────────────────────────────────────────

def nl_query(question: str, unit_id: str, chat_history: list[dict],
             drawing_ids: list[str] | None = None) -> dict:
    status, data = _post(
        "/api/v1/query/nl",
        json={
            "question":    question,
            "unit_id":     unit_id,
            "chat_history": chat_history,
            "drawing_ids": drawing_ids or [],
        },
        timeout=60,
    )
    if status == 200:
        return data
    return {"answer": f"Backend error ({status}): {data.get('detail', data.get('error', 'Unknown'))}", "query_type": "error", "sources": []}


def report_bug(component: str, description: str, steps: str, severity: str,
               unit_name: str | None = None, page: str | None = None) -> tuple[bool, str]:
    status, data = _post("/api/v1/query/bug", json={
        "component": component,
        "description": description,
        "steps_to_reproduce": steps,
        "severity": severity,
        "unit_name": unit_name,
        "page_context": page,
    })
    if status == 201:
        url = data.get("issue_url", "")
        return True, url
    return False, data.get("message", "Bug report saved.")


# ── Incidents ─────────────────────────────────────────────────────────────────

def list_incidents(unit_id: str | None = None, status: str | None = None) -> list[dict]:
    params: dict = {}
    if unit_id:
        params["unit_id"] = unit_id
    if status:
        params["status"] = status
    code, data = _get("/api/v1/incidents/", params)
    return data if code == 200 else []


def create_incident(unit_id: str, title: str, description: str,
                    severity: str, related_tags: list[str]) -> tuple[bool, dict]:
    code, data = _post("/api/v1/incidents/", json={
        "unit_id": unit_id, "title": title, "description": description,
        "severity": severity, "related_tags": related_tags,
    })
    return code == 201, data


def resolve_incident(incident_id: str, resolution: str) -> tuple[bool, dict]:
    code, data = _patch(f"/api/v1/incidents/{incident_id}/resolve", json={"resolution": resolution})
    return code == 200, data


# ── Health ────────────────────────────────────────────────────────────────────

def get_health() -> dict:
    status, data = _get("/health")
    return data if status == 200 else {"status": "unreachable"}
