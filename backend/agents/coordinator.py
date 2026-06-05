"""
Coordinator Agent — deterministic routing + LLM formatting.

Architecture (no tool-calling — works with any Ollama model):
  User question
      │
  classify_query()  →  list | path | impact | sop | detail | general
      │
  _gather_context() →  calls specialists directly (no LLM needed)
      │
  ChatOllama.invoke()  →  formats gathered data into natural language
      │
  NLQueryResponse {answer, query_type, sources}
"""
import re
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from backend.config import get_settings
from backend.graph.builder import GraphBuilder
from backend.rag.engine import RAGEngine
from backend.agents.graph_agent import GraphAgent
from backend.agents.document_agent import DocumentAgent
from backend.agents.incident_agent import IncidentAgent
from backend.agents.pid_agent import PIDAgent

# ── Tag extractor ──────────────────────────────────────────────────────────────
# Matches both formats:
#   Standard ISA  : P-101, TIC-301, FCV-101A
#   Area-type-seq : 04-VV-002, 04-P-001, 04-TIC-001
_TAG_RE = re.compile(
    r'\b(?:\d{2,4}-[A-Z]{1,5}-\d{2,4}[A-Z]?'   # 04-VV-002 style
    r'|[A-Z]{1,5}-\d{2,4}[A-Z]?)\b',             # P-101 style
    re.IGNORECASE,
)

# ── Query type classifier ──────────────────────────────────────────────────────
_LIST_PAT   = re.compile(r"\b(list|all|show|how many|count|what .{0,20} in)\b", re.I)
_PATH_PAT   = re.compile(r"\b(path|route|from .{1,30} to|trace|flow)\b", re.I)
_IMPACT_PAT = re.compile(r"\b(impact|fail|isolat|trip|affect)\b|what happens?|downstream of", re.I)
_SOP_PAT    = re.compile(r"\b(sop|procedure|manual|how to|startup|shutdown|isolation|step)\b", re.I)
_DETAIL_PAT = re.compile(r"\b(what is|tell me about|describe|detail|info|about)\b", re.I)


def classify_query(question: str) -> str:
    if _PATH_PAT.search(question):    return "path"
    if _IMPACT_PAT.search(question):  return "impact"
    if _SOP_PAT.search(question):     return "sop"
    if _LIST_PAT.search(question):    return "list"
    if _DETAIL_PAT.search(question):  return "detail"
    return "general"


# ── Context gatherer ───────────────────────────────────────────────────────────

def _gather_context(
    question: str,
    query_type: str,
    unit_name: str,
    graph_agent: GraphAgent,
    doc_agent: DocumentAgent,
    incident_agent: IncidentAgent,
    pid_agent: PIDAgent,
) -> tuple[str, list[dict]]:
    """
    Gathers structured data from specialists WITHOUT calling the LLM.
    Returns (context_text, sources_list).
    """
    lines:   list[str]  = []
    sources: list[dict] = []
    tags_in_question = _TAG_RE.findall(question.upper())

    if query_type == "list":
        # Find which equipment type is being asked about
        etype_found = None
        for etype in ("pump", "vessel", "valve", "instrument", "exchanger", "compressor", "line"):
            if etype in question.lower():
                etype_found = etype
                break

        if etype_found:
            result = graph_agent.list_by_type(etype_found)
            tags = result.get("tags", [])
            lines.append(
                f"Found {result['count']} {etype_found}(s) in unit {unit_name}:\n"
                + (", ".join(tags) if tags else "None found.")
            )
        else:
            # List all equipment
            result = graph_agent.get_all_tags()
            by_type: dict[str, list] = {}
            for t in result.get("tags", []):
                by_type.setdefault(t.get("type", "other"), []).append(t["tag"])
            for typ, tag_list in by_type.items():
                lines.append(f"{typ.title()}s: {', '.join(tag_list)}")

    elif query_type == "detail":
        if tags_in_question:
            for tag in tags_in_question[:3]:
                result = graph_agent.search_equipment(tag)
                if result["found"]:
                    lines.append(
                        f"Tag: {result['tag']} | Type: {result['tag_type']} | "
                        f"Description: {result['description']}\n"
                        f"  Upstream: {result['upstream'] or 'none'}\n"
                        f"  Downstream: {result['downstream'] or 'none'}"
                    )
                    prov = pid_agent.get_tag_provenance(tag, unit_name)
                    if prov.get("found"):
                        src  = prov.get("source_document", "")
                        page = prov.get("page_number", "?")
                        lines.append(f"  Source: {src} page {page}")
                        sources.append({"source": src, "page": str(page)})
                else:
                    # Give a helpful explanation with what IS available
                    all_tags = graph_agent.get_all_tags()
                    tag_count = all_tags.get("stats", {}).get("nodes", 0)
                    sheets = pid_agent.list_pid_sheets(unit_name)
                    sheet_count = sheets.get("sheet_count", 0)
                    lines.append(
                        f"Tag '{tag}' is NOT in the current knowledge graph for unit {unit_name}.\n"
                        f"  Currently indexed: {tag_count} tags from {sheet_count} P&ID sheets.\n"
                        f"  This tag may be on a P&ID sheet that has not been uploaded yet.\n"
                        f"  ACTION: Upload the P&ID sheet containing '{tag}' via the Upload P&IDs page."
                    )
        else:
            lines.append(f"Please specify a tag name (e.g. P-101, 04-VV-002, PV-7201B).")

    elif query_type == "path":
        if len(tags_in_question) >= 2:
            src, tgt = tags_in_question[0], tags_in_question[1]
            result = graph_agent.trace_path(src, tgt)
            if result["found"]:
                lines.append(
                    f"Process path from {src} to {tgt} ({result['length']} steps):\n"
                    f"  {' → '.join(result['path'])}"
                )
            else:
                lines.append(f"No direct process path found from {src} to {tgt}.")
        elif len(tags_in_question) == 1:
            tag = tags_in_question[0]
            nb = graph_agent.search_equipment(tag)
            lines.append(
                f"Connections for {tag}:\n"
                f"  Upstream: {nb['upstream'] or 'none'}\n"
                f"  Downstream: {nb['downstream'] or 'none'}"
            )
        else:
            lines.append("Please specify two tag names for path tracing (e.g. 'path from P-101 to V-201').")

    elif query_type == "impact":
        tag = tags_in_question[0] if tags_in_question else None
        if tag:
            result = graph_agent.analyze_impact(tag)
            if result["found"]:
                by_type = result.get("affected_by_type", {})
                impact_lines = [
                    f"  {typ.title()}s: {', '.join(tags)}" for typ, tags in by_type.items()
                ]
                lines.append(
                    f"Impact analysis for {tag}:\n"
                    f"  Severity: {result['severity'].upper()}\n"
                    f"  {result['affected_count']} equipment affected downstream:\n"
                    + "\n".join(impact_lines)
                )
            else:
                all_tags = graph_agent.get_all_tags()
                tag_count = all_tags.get("stats", {}).get("nodes", 0)
                lines.append(
                    f"Tag '{tag}' is NOT in the current knowledge graph for {unit_name} "
                    f"({tag_count} tags indexed).\n"
                    f"  Upload the P&ID sheet containing '{tag}' to enable impact analysis."
                )
        else:
            lines.append("Please specify a tag name for impact analysis (e.g. 'impact of PV-7201B failing').")

    elif query_type == "sop":
        result = doc_agent.search_sop(question, n_results=3)
        if result["results_found"] > 0:
            for r in result["results"]:
                src  = r.get("source", "")
                page = r.get("page", "?")
                lines.append(f"[{src} p.{page}]\n{r['content']}")
                sources.append({"source": src, "page": str(page)})
        else:
            lines.append(
                "No relevant SOP or manual found. "
                "Upload SOPs in the Documents page and ensure they are indexed."
            )

    else:
        # general / fallback — search by tag or semantic
        if tags_in_question:
            for tag in tags_in_question[:2]:
                result = graph_agent.search_equipment(tag)
                if result["found"]:
                    lines.append(
                        f"{result['tag']} ({result['tag_type']}): {result['description']}\n"
                        f"  Upstream: {result['upstream'] or 'none'}\n"
                        f"  Downstream: {result['downstream'] or 'none'}"
                    )
                else:
                    all_tags = graph_agent.get_all_tags()
                    tag_count = all_tags.get("stats", {}).get("nodes", 0)
                    sheets = pid_agent.list_pid_sheets(unit_name)
                    sheet_names = [s["filename"] for s in sheets.get("sheets", [])[:4]]
                    lines.append(
                        f"Tag '{tag}' is NOT in the current knowledge graph.\n"
                        f"  Unit {unit_name} has {tag_count} tags from {sheets.get('sheet_count',0)} sheets: "
                        f"{', '.join(sheet_names) or 'none uploaded yet'}.\n"
                        f"  To find '{tag}', upload the P&ID sheet that contains it."
                    )
        else:
            # Semantic search over equipment descriptions
            sem = doc_agent.search_equipment_semantic(question, n_results=5)
            for r in sem.get("results", []):
                lines.append(f"{r['tag']} ({r['tag_type']}): {r['description']}")

        # Also check incidents
        if tags_in_question:
            inc = incident_agent.find_related_incidents(tags_in_question[0], unit_name)
            if inc["incidents_found"] > 0:
                lines.append(f"\nRelated incidents for {tags_in_question[0]}:")
                for i in inc["incidents"]:
                    lines.append(f"  [{i['severity'].upper()}] {i['title']} ({i['status']})")

    return "\n".join(lines) if lines else f"No data found for this query in unit {unit_name}.", sources


# ── Coordinator Agent ──────────────────────────────────────────────────────────

class CoordinatorAgent:
    def __init__(self, graph: GraphBuilder, rag: RAGEngine):
        self.graph    = graph
        self.rag      = rag
        self.settings = get_settings()
        self._llm: ChatOllama | None = None

    def _get_llm(self) -> ChatOllama:
        if self._llm is None:
            self._llm = ChatOllama(
                base_url=self.settings.ollama_base_url,
                model=self.settings.ollama_chat_model,
                temperature=0,
                num_ctx=4096,
            )
        return self._llm

    def run(
        self,
        question: str,
        unit_name: str,
        chat_history: list[dict] | None = None,
    ) -> dict:
        """
        Synchronous — run via asyncio.to_thread() from async routes.
        Returns: {answer, query_type, sources, success}
        """
        chat_history = chat_history or []
        query_type   = classify_query(question)

        graph_agent    = GraphAgent(self.graph, unit_name)
        doc_agent      = DocumentAgent(self.rag, unit_name)
        incident_agent = IncidentAgent()
        pid_agent      = PIDAgent()

        # Step 1: gather data deterministically (no LLM needed)
        context, sources = _gather_context(
            question, query_type, unit_name,
            graph_agent, doc_agent, incident_agent, pid_agent,
        )

        # Step 2: use LLM to format a readable answer from the data
        system_msg = SystemMessage(content=(
            f"You are an expert P&ID engineering assistant for unit {unit_name} at a refinery.\n"
            "Answer the engineer's question using ONLY the data provided below.\n"
            "Be concise, use engineering terminology, and present results clearly.\n"
            "If the data shows 'not found' or 'no data', say so honestly.\n"
            "Do not make up tag names or equipment that isn't in the data."
        ))
        user_msg = HumanMessage(content=(
            f"Question: {question}\n\n"
            f"Data from P&ID knowledge graph:\n{context}"
        ))

        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
        _pool = ThreadPoolExecutor(max_workers=1)
        try:
            llm = self._get_llm()
            future = _pool.submit(llm.invoke, [system_msg, user_msg])
            response = future.result(timeout=50)
            answer = response.content.strip()
            # Strip Qwen3 thinking tags if present (<think>...</think>)
            answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()
        except FuturesTimeout:
            logger.warning("LLM formatting timed out after 50s, returning raw data")
            answer = f"**{unit_name} — {query_type.title()} Query**\n\n{context}"
        except Exception as exc:
            logger.warning(f"LLM formatting failed ({exc}), returning raw data")
            answer = f"**{unit_name} — {query_type.title()} Query**\n\n{context}"
        finally:
            _pool.shutdown(wait=False)

        return {
            "answer":     answer,
            "query_type": query_type,
            "sources":    sources,
            "success":    True,
        }


def _extract_sources(intermediate_steps: list) -> list[dict]:
    """Kept for backward compatibility with tests."""
    return []
