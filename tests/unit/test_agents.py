import pytest
from unittest.mock import MagicMock, patch


# ── Query classifier ───────────────────────────────────────────────────────────

def test_classify_list_query():
    from backend.agents.coordinator import classify_query
    assert classify_query("List all pumps in CDU") == "list"
    assert classify_query("Show me all control valves") == "list"
    assert classify_query("How many instruments are there?") == "list"


def test_classify_path_query():
    from backend.agents.coordinator import classify_query
    assert classify_query("What is the path from P-101 to V-201?") == "path"
    assert classify_query("Trace the flow from the feed drum to the column") == "path"


def test_classify_impact_query():
    from backend.agents.coordinator import classify_query
    assert classify_query("What happens if P-101 fails?") == "impact"
    assert classify_query("What is downstream of V-101 if it is isolated?") == "impact"
    assert classify_query("Impact of tripping the reactor feed pump") == "impact"


def test_classify_sop_query():
    from backend.agents.coordinator import classify_query
    assert classify_query("What is the startup procedure for the vacuum system?") == "sop"
    assert classify_query("Show me the isolation manual for CDU column") == "sop"


def test_classify_detail_query():
    from backend.agents.coordinator import classify_query
    assert classify_query("Tell me about TIC-301") == "detail"
    assert classify_query("What is P-101?") == "detail"


def test_classify_general_query():
    from backend.agents.coordinator import classify_query
    assert classify_query("Hello, how are you?") == "general"


# ── GraphAgent tools ──────────────────────────────────────────────────────────

@pytest.fixture
def graph_agent(tmp_path):
    with patch("backend.graph.builder.get_settings") as mock_settings:
        mock_settings.return_value.graph_dir = str(tmp_path)
        from backend.graph.builder import GraphBuilder
        from backend.agents.graph_agent import GraphAgent
        gb = GraphBuilder()
        gb.add_equipment("CDU", "P-101", "pump", description="Feed pump")
        gb.add_equipment("CDU", "V-101", "vessel", description="Feed drum")
        gb.add_equipment("CDU", "E-101", "exchanger", description="Feed pre-heater")
        gb.add_connection("CDU", "P-101", "E-101")
        gb.add_connection("CDU", "E-101", "V-101")
        return GraphAgent(gb, "CDU")


def test_graph_agent_search_found(graph_agent):
    result = graph_agent.search_equipment("P-101")
    assert result["found"] is True
    assert result["tag"] == "P-101"
    assert result["tag_type"] == "pump"
    assert "E-101" in result["downstream"]


def test_graph_agent_search_not_found(graph_agent):
    result = graph_agent.search_equipment("UNKNOWN-999")
    assert result["found"] is False


def test_graph_agent_list_by_type(graph_agent):
    result = graph_agent.list_by_type("pump")
    assert result["count"] == 1
    assert "P-101" in result["tags"]


def test_graph_agent_list_by_type_empty(graph_agent):
    result = graph_agent.list_by_type("compressor")
    assert result["count"] == 0


def test_graph_agent_trace_path(graph_agent):
    result = graph_agent.trace_path("P-101", "V-101")
    assert result["found"] is True
    assert result["path"] == ["P-101", "E-101", "V-101"]
    assert result["length"] == 2


def test_graph_agent_trace_path_not_found(graph_agent):
    result = graph_agent.trace_path("V-101", "P-101")  # reverse — no path
    assert result["found"] is False


def test_graph_agent_analyze_impact(graph_agent):
    result = graph_agent.analyze_impact("P-101")
    assert result["found"] is True
    assert "E-101" in result["affected"]
    assert "V-101" in result["affected"]
    assert result["severity"] in ("low", "medium", "high")


def test_graph_agent_get_all_tags(graph_agent):
    result = graph_agent.get_all_tags()
    assert result["unit"] == "CDU"
    tag_names = [t["tag"] for t in result["tags"]]
    assert "P-101" in tag_names
    assert "V-101" in tag_names


# ── DocumentAgent ─────────────────────────────────────────────────────────────

def test_document_agent_search_sop_empty():
    from backend.agents.document_agent import DocumentAgent
    mock_rag = MagicMock()
    mock_rag.search_documents.return_value = []
    agent = DocumentAgent(mock_rag, "CDU")
    result = agent.search_sop("startup procedure")
    assert result["results_found"] == 0


def test_document_agent_search_sop_with_results():
    from backend.agents.document_agent import DocumentAgent
    mock_rag = MagicMock()
    mock_rag.search_documents.return_value = [
        {"content": "Open isolation valve V-101 before starting pump.", "source": "CDU_SOP.pdf", "page": 3}
    ]
    agent = DocumentAgent(mock_rag, "CDU")
    result = agent.search_sop("startup pump")
    assert result["results_found"] == 1
    assert result["results"][0]["source"] == "CDU_SOP.pdf"


# ── Source extraction ─────────────────────────────────────────────────────────

def test_extract_sources_from_pid_sheet():
    from backend.agents.coordinator import _extract_sources
    action = MagicMock()
    action.tool = "find_pid_sheet"
    observation = "Tag P-101 (pump) found on P&ID-CDU-003.pdf page 5."
    steps = [(action, observation)]
    sources = _extract_sources(steps)
    assert len(sources) == 1
    assert sources[0]["source"] == "P&ID-CDU-003.pdf"
    assert sources[0]["page"] == "5"


def test_extract_sources_from_sop():
    from backend.agents.coordinator import _extract_sources
    action = MagicMock()
    action.tool = "search_sop"
    observation = "[CDU_Startup_SOP.pdf p.12]\nOpen valve before starting pump."
    steps = [(action, observation)]
    sources = _extract_sources(steps)
    assert len(sources) == 1
    assert sources[0]["source"] == "CDU_Startup_SOP.pdf"
    assert sources[0]["page"] == "12"


def test_extract_sources_deduplicates():
    from backend.agents.coordinator import _extract_sources
    action = MagicMock()
    action.tool = "find_pid_sheet"
    observation = "Tag P-101 (pump) found on P&ID-CDU-003.pdf page 5."
    steps = [(action, observation), (action, observation)]  # same source twice
    sources = _extract_sources(steps)
    assert len(sources) == 1
