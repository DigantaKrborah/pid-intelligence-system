"""
test_flow.py — End-to-end integration test for the P&ID Intelligence System.

Simulates the full user flow against a RUNNING backend (localhost:8000).
Start the backend first:  cd backend && uvicorn main:app --reload

Run with pytest:
    cd backend
    python -m pytest tests/test_flow.py -v

Or run directly:
    cd backend
    python tests/test_flow.py
"""

import sys
import json
import requests
import pytest

BASE_URL = "http://localhost:8000"

# Seed data credentials (from db/seed.sql)
ADMIN_USER = "admin"
ADMIN_PASS = "Admin@123"

# Shared state between tests (pytest class scope keeps this alive)
_state = {
    "token":      None,
    "unit_id":    None,
    "unit_code":  None,
}


# ── Helper: authenticated session ────────────────────────────────────────────

def auth_headers() -> dict:
    """Return Authorization header dict using the stored token."""
    return {"Authorization": f"Bearer {_state['token']}"}


def get(path: str, **kwargs) -> requests.Response:
    return requests.get(BASE_URL + path, headers=auth_headers(), **kwargs)


def post(path: str, json_body=None, **kwargs) -> requests.Response:
    return requests.post(BASE_URL + path, json=json_body, headers=auth_headers(), **kwargs)


# ── Backend health check (no auth needed) ────────────────────────────────────

def test_00_server_is_running():
    """Verify the FastAPI server is reachable before running anything else."""
    try:
        r = requests.get(BASE_URL + "/", timeout=5)
    except requests.exceptions.ConnectionError:
        pytest.fail(
            "Cannot connect to http://localhost:8000 — "
            "start the backend first:  cd backend && uvicorn main:app --reload"
        )
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    body = r.json()
    assert body.get("status") == "ok", f"Unexpected health response: {body}"
    print(f"\n  ✓ Server running — {body}")


# ── Step 1: Login ─────────────────────────────────────────────────────────────

def test_01_login_admin():
    """POST /api/auth/login — should return a JWT token."""
    r = requests.post(
        BASE_URL + "/api/auth/login",
        json={"username": ADMIN_USER, "password": ADMIN_PASS},
    )
    assert r.status_code == 200, f"Login failed {r.status_code}: {r.text}"

    body = r.json()
    assert "access_token" in body, f"No access_token in response: {body}"
    assert body.get("token_type") == "bearer"
    assert body["user"]["role"] == "admin"

    _state["token"] = body["access_token"]
    print(f"\n  ✓ Logged in as {body['user']['username']} (role={body['user']['role']})")


def test_01b_login_wrong_password():
    """Login with wrong password should return 401."""
    r = requests.post(
        BASE_URL + "/api/auth/login",
        json={"username": ADMIN_USER, "password": "wrong_password"},
    )
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    print(f"\n  ✓ Wrong-password correctly rejected with 401")


def test_01c_get_me():
    """GET /api/auth/me — should return current user info."""
    r = get("/api/auth/me")
    assert r.status_code == 200, f"GET /me failed: {r.status_code} {r.text}"
    body = r.json()
    assert body["username"] == ADMIN_USER
    print(f"\n  ✓ /me returned: {body['full_name']} ({body['role']})")


# ── Step 2: Process units ─────────────────────────────────────────────────────

def test_02_list_units():
    """GET /api/units/ — should return the seeded units."""
    r = get("/api/units/")
    assert r.status_code == 200, f"list_units failed: {r.status_code} {r.text}"

    units = r.json()
    assert isinstance(units, list), f"Expected list, got: {type(units)}"
    assert len(units) > 0, "Expected at least one unit from seed data"

    # Save the first unit for later tests
    _state["unit_id"]   = units[0]["id"]
    _state["unit_code"] = units[0]["unit_code"]
    print(f"\n  ✓ {len(units)} units found. Using: {units[0]['unit_code']} ({units[0]['unit_name']})")


def test_02b_create_test_unit():
    """POST /api/units/ — create a TEST unit (if it doesn't exist)."""
    # First check if TEST already exists
    r = get("/api/units/")
    existing = [u for u in r.json() if u["unit_code"] == "TEST"]
    if existing:
        print(f"\n  ✓ TEST unit already exists (id={existing[0]['id'][:8]}…) — skipping create")
        return

    r = post("/api/units/", {
        "unit_code":   "TEST",
        "unit_name":   "Test Unit (automated test)",
        "description": "Created by test_flow.py — safe to delete",
    })
    assert r.status_code == 201, f"create_unit failed: {r.status_code} {r.text}"
    body = r.json()
    assert body["unit_code"] == "TEST"
    print(f"\n  ✓ Created TEST unit (id={body['id'][:8]}…)")


def test_02c_create_duplicate_unit():
    """POST /api/units/ with duplicate code should return 409."""
    r = post("/api/units/", {
        "unit_code": "CDU",   # already in seed data
        "unit_name": "Duplicate",
    })
    assert r.status_code == 409, f"Expected 409 for duplicate, got {r.status_code}"
    print(f"\n  ✓ Duplicate unit_code correctly rejected with 409")


# ── Step 3: Drawings endpoints ────────────────────────────────────────────────

def test_03_list_drawings():
    """GET /api/drawings/ — should return list (may be empty)."""
    r = get("/api/drawings/")
    assert r.status_code == 200, f"list_drawings failed: {r.status_code} {r.text}"
    drawings = r.json()
    assert isinstance(drawings, list)
    print(f"\n  ✓ /drawings/ returned {len(drawings)} drawing(s)")


def test_03b_list_drawings_filtered():
    """GET /api/drawings/?unit_id=... — filter should work."""
    unit_id = _state["unit_id"]
    r = get(f"/api/drawings/?unit_id={unit_id}")
    assert r.status_code == 200, f"filtered drawings failed: {r.status_code}"
    drawings = r.json()
    assert isinstance(drawings, list)
    # Every returned drawing should belong to this unit
    for d in drawings:
        assert d["unit_id"] == unit_id, f"Drawing unit_id mismatch: {d}"
    print(f"\n  ✓ Filtered drawings for {_state['unit_code']}: {len(drawings)} result(s)")


# ── Step 4: Documents endpoints ───────────────────────────────────────────────

def test_04_list_documents():
    """GET /api/documents/ — should return list (may be empty)."""
    r = get("/api/documents/")
    assert r.status_code == 200, f"list_documents failed: {r.status_code} {r.text}"
    docs = r.json()
    assert isinstance(docs, list)
    print(f"\n  ✓ /documents/ returned {len(docs)} document(s)")


# ── Step 5: Tag search ────────────────────────────────────────────────────────

def test_05_tag_search_returns_list():
    """GET /api/tags/search?q=... — should return a list (may be empty before extraction)."""
    r = get("/api/tags/search?q=P-10")
    assert r.status_code == 200, f"tag search failed: {r.status_code} {r.text}"
    results = r.json()
    assert isinstance(results, list)
    print(f"\n  ✓ Tag search 'P-10' returned {len(results)} result(s)")


def test_05b_tag_search_requires_query():
    """GET /api/tags/search without q= should return 422."""
    r = get("/api/tags/search")
    assert r.status_code == 422, f"Expected 422 for missing q param, got {r.status_code}"
    print(f"\n  ✓ Missing ?q= param correctly rejected with 422")


def test_05c_unit_tag_summary():
    """GET /api/tags/unit/{id}/summary — should return breakdown."""
    unit_id = _state["unit_id"]
    r = get(f"/api/tags/unit/{unit_id}/summary")
    assert r.status_code == 200, f"tag summary failed: {r.status_code} {r.text}"
    body = r.json()
    assert "total_tags" in body
    assert "breakdown" in body
    assert "equipment" in body["breakdown"]
    print(f"\n  ✓ Tag summary for {_state['unit_code']}: {body['total_tags']} total tags")


# ── Step 6: Settings endpoints ────────────────────────────────────────────────

def test_06_get_llm_settings():
    """GET /api/settings/llm — should return config or not-configured response."""
    r = get("/api/settings/llm")
    assert r.status_code == 200, f"GET settings/llm failed: {r.status_code} {r.text}"
    body = r.json()
    assert "configured" in body
    print(f"\n  ✓ LLM settings: configured={body['configured']}, provider={body.get('provider')}")


def test_06b_get_llm_models():
    """GET /api/settings/llm/models — should return provider→models catalogue."""
    r = get("/api/settings/llm/models")
    assert r.status_code == 200, f"GET settings/llm/models failed: {r.status_code}"
    body = r.json()
    assert "claude" in body
    assert "openai" in body
    assert "gemini" in body
    assert isinstance(body["claude"], list)
    assert len(body["claude"]) > 0
    print(f"\n  ✓ Model catalogue: {len(body['claude'])} Claude, {len(body['openai'])} OpenAI, {len(body['gemini'])} Gemini models")


# ── Step 7: Audit log ─────────────────────────────────────────────────────────

def test_07_audit_log_populated():
    """GET /api/audit/ — should return flat list with at least one LOGIN entry."""
    r = get("/api/audit/?limit=50")
    assert r.status_code == 200, f"GET /audit/ failed: {r.status_code} {r.text}"

    logs = r.json()
    assert isinstance(logs, list), f"Expected list, got: {type(logs)}"
    assert len(logs) > 0, "Audit log is empty — expected at least a LOGIN entry from test_01"

    actions = [entry["action"] for entry in logs]
    assert "LOGIN" in actions, f"No LOGIN entry in audit log. Found: {set(actions)}"
    print(f"\n  ✓ Audit log has {len(logs)} entries. Actions seen: {sorted(set(actions))}")


def test_07b_audit_log_filters():
    """GET /api/audit/?action=LOGIN — filter by action should work."""
    r = get("/api/audit/?action=LOGIN&limit=10")
    assert r.status_code == 200
    logs = r.json()
    assert isinstance(logs, list)
    for entry in logs:
        assert "LOGIN" in entry["action"], f"Unexpected action in filtered result: {entry['action']}"
    print(f"\n  ✓ Audit filter ?action=LOGIN returned {len(logs)} entry/entries")


def test_07c_audit_requires_admin():
    """GET /api/audit/ without auth should return 403 (bearer missing → 403 from HTTPBearer)."""
    r = requests.get(BASE_URL + "/api/audit/?limit=5")
    # HTTPBearer auto_error=True returns 403 when header is absent
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"
    print(f"\n  ✓ Audit endpoint correctly requires auth (got {r.status_code})")


# ── Step 8: Users endpoint ────────────────────────────────────────────────────

def test_08_list_users():
    """GET /api/users/ — admin should see all users."""
    r = get("/api/users/")
    assert r.status_code == 200, f"list_users failed: {r.status_code} {r.text}"
    users = r.json()
    assert isinstance(users, list)
    assert len(users) > 0
    usernames = [u["username"] for u in users]
    assert ADMIN_USER in usernames, f"Admin user not in list: {usernames}"
    print(f"\n  ✓ /users/ returned {len(users)} user(s): {usernames}")


# ── Step 9: Extraction status endpoint ────────────────────────────────────────

def test_09_extraction_status_404_for_unknown():
    """GET /api/extraction/status/{fake_id} — unknown drawing should return 404."""
    fake_id = "00000000-0000-0000-0000-000000000999"
    r = get(f"/api/extraction/status/{fake_id}")
    assert r.status_code == 404, f"Expected 404 for unknown drawing, got {r.status_code}"
    print(f"\n  ✓ Extraction status for unknown ID correctly returns 404")


# ── Run as standalone script ───────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("Server running",            test_00_server_is_running),
        ("Login admin",               test_01_login_admin),
        ("Login wrong password",      test_01b_login_wrong_password),
        ("GET /me",                   test_01c_get_me),
        ("List units",                test_02_list_units),
        ("Create TEST unit",          test_02b_create_test_unit),
        ("Duplicate unit rejected",   test_02c_create_duplicate_unit),
        ("List drawings",             test_03_list_drawings),
        ("List drawings filtered",    test_03b_list_drawings_filtered),
        ("List documents",            test_04_list_documents),
        ("Tag search",                test_05_tag_search_returns_list),
        ("Tag search no q= → 422",   test_05b_tag_search_requires_query),
        ("Unit tag summary",          test_05c_unit_tag_summary),
        ("GET LLM settings",          test_06_get_llm_settings),
        ("GET LLM models",            test_06b_get_llm_models),
        ("Audit log populated",       test_07_audit_log_populated),
        ("Audit log filter",          test_07b_audit_log_filters),
        ("Audit requires auth",       test_07c_audit_requires_admin),
        ("List users",                test_08_list_users),
        ("Extraction 404",            test_09_extraction_status_404_for_unknown),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as exc:
            print(f"  FAIL  {name}")
            print(f"         → {exc}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")
    sys.exit(0 if failed == 0 else 1)
