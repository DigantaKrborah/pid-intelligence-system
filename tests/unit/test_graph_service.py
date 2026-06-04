"""Tests for graph_service.py — graph rebuild from PostgreSQL."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_async_session():
    """
    Build an AsyncMock session where execute() returns a plain MagicMock
    (not an AsyncMock), so result methods like scalar_one_or_none() are
    regular callables that return values immediately — not coroutines.
    """
    session = AsyncMock()
    result  = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    return session, result


def _make_mock_tag(tag: str, tag_type: str, description: str = ""):
    t = MagicMock()
    t.id          = uuid.uuid4()
    t.tag         = tag
    t.tag_type    = tag_type
    t.description = description
    t.document_id = uuid.uuid4()
    t.page_number = 1
    return t


def _make_mock_unit(name: str):
    u = MagicMock()
    u.id   = uuid.uuid4()
    u.name = name
    return u


def _make_mock_connection(src_id: uuid.UUID, tgt_id: uuid.UUID):
    c = MagicMock()
    c.source_tag_id   = src_id
    c.target_tag_id   = tgt_id
    c.connection_type = "pipeline"
    c.line_number     = ""
    return c


# ── rebuild_graph_from_db ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rebuild_graph_unit_not_found():
    """Returns 0 immediately when unit does not exist in DB."""
    session, result = _make_async_session()
    result.scalar_one_or_none.return_value = None

    from backend.services.graph_service import rebuild_graph_from_db
    count = await rebuild_graph_from_db("UNKNOWN", session)
    assert count == 0


@pytest.mark.asyncio
async def test_rebuild_graph_no_tags():
    """Returns 0 and skips GraphBuilder when unit exists but has no tags."""
    session, _ = _make_async_session()
    unit = _make_mock_unit("CDU")

    # First execute → unit; second → empty tag list
    results = [
        _sync_result(scalar=unit),
        _sync_result(scalars_list=[]),
    ]
    session.execute.side_effect = results

    with patch("backend.services.graph_service._graph") as mock_graph:
        from backend.services.graph_service import rebuild_graph_from_db
        count = await rebuild_graph_from_db("CDU", session)

    assert count == 0
    mock_graph.rebuild_from_tags.assert_not_called()


@pytest.mark.asyncio
async def test_rebuild_graph_builds_correctly():
    """Rebuilds graph with correct nodes and edges from DB records."""
    session, _ = _make_async_session()
    unit    = _make_mock_unit("CDU")
    t_p101  = _make_mock_tag("P-101", "pump",   "Feed pump")
    t_v101  = _make_mock_tag("V-101", "vessel", "Feed drum")
    conn    = _make_mock_connection(t_p101.id, t_v101.id)

    results = [
        _sync_result(scalar=unit),
        _sync_result(scalars_list=[t_p101, t_v101]),
        _sync_result(scalars_list=[conn]),
    ]
    session.execute.side_effect = results

    with patch("backend.services.graph_service._graph") as mock_graph:
        from backend.services.graph_service import rebuild_graph_from_db
        count = await rebuild_graph_from_db("CDU", session)

    assert count == 2
    mock_graph.rebuild_from_tags.assert_called_once()
    tags_passed = mock_graph.rebuild_from_tags.call_args.args[1]
    assert any(t["tag"] == "P-101" for t in tags_passed)
    assert any(t["tag"] == "V-101" for t in tags_passed)


# ── ensure_all_graphs_loaded ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ensure_rebuilds_missing_graph():
    """Calls rebuild when a unit's graph JSON file does not exist."""
    session, _ = _make_async_session()
    unit = _make_mock_unit("CDU")
    session.execute.return_value.scalars.return_value.all.return_value = [unit]

    with patch("backend.services.graph_service._graph") as mock_graph, \
         patch("backend.services.graph_service.rebuild_graph_from_db",
               new_callable=AsyncMock) as mock_rebuild:
        mock_graph._graph_path.return_value.exists.return_value = False
        from backend.services.graph_service import ensure_all_graphs_loaded
        await ensure_all_graphs_loaded(session)

    mock_rebuild.assert_called_once_with("CDU", session)


@pytest.mark.asyncio
async def test_ensure_prewarms_existing_graph():
    """Pre-warms cache (load_or_create) when graph JSON already exists."""
    session, _ = _make_async_session()
    unit = _make_mock_unit("VDU")
    session.execute.return_value.scalars.return_value.all.return_value = [unit]

    with patch("backend.services.graph_service._graph") as mock_graph, \
         patch("backend.services.graph_service.rebuild_graph_from_db",
               new_callable=AsyncMock) as mock_rebuild:
        mock_graph._graph_path.return_value.exists.return_value = True
        from backend.services.graph_service import ensure_all_graphs_loaded
        await ensure_all_graphs_loaded(session)

    mock_rebuild.assert_not_called()
    mock_graph.load_or_create.assert_called_once_with("VDU")


# ── Helper ────────────────────────────────────────────────────────────────────

def _sync_result(scalar=None, scalars_list=None):
    """Build a plain MagicMock that mimics SQLAlchemy execute() result."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar
    r.scalars.return_value.all.return_value = scalars_list or []
    return r
