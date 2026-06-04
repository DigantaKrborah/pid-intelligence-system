"""
Coordinator Agent — orchestrates specialist agents via LangChain tool-calling.

Architecture:
  User question
      │
  CoordinatorAgent (Ollama llama3.2)
      │
      ├── search_equipment     → GraphAgent.search_equipment()
      ├── list_by_type         → GraphAgent.list_by_type()
      ├── trace_process_path   → GraphAgent.trace_path()
      ├── analyze_impact       → GraphAgent.analyze_impact()
      ├── search_sop           → DocumentAgent.search_sop()
      ├── find_pid_sheet       → PIDAgent.get_tag_provenance()
      └── find_incidents       → IncidentAgent.find_related_incidents()
"""
import json
import re
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from loguru import logger

from backend.config import get_settings
from backend.graph.builder import GraphBuilder
from backend.rag.engine import RAGEngine
from backend.agents.graph_agent import GraphAgent
from backend.agents.document_agent import DocumentAgent
from backend.agents.incident_agent import IncidentAgent
from backend.agents.pid_agent import PIDAgent


SYSTEM_PROMPT = """\
You are an expert P&ID (Piping & Instrumentation Diagram) engineering assistant for process \
engineers at refineries and chemical plants.

You have tools to:
- search_equipment: get connections and details for a specific tag (e.g. P-101)
- list_by_type: list all equipment of a type (pump, vessel, valve, instrument, exchanger, compressor)
- trace_process_path: find the process flow path between two tags
- analyze_impact: determine what equipment is affected if a tag fails or is isolated
- search_sop: search SOPs and manuals for operational procedures
- find_pid_sheet: find which P&ID sheet a tag came from and its source document
- find_incidents: find past incidents related to a specific equipment tag

Guidelines:
- Always use tools to answer — do not guess tag names or equipment details
- Cite the source P&ID sheet or document name when available
- Use engineering terminology; be concise
- For list queries, present results as a table or bullet list
- For path queries, show the full path with arrows: A → B → C
- Current unit context is injected in the system prompt — honour it
"""

# ── Query type classifier ──────────────────────────────────────────────────────

_LIST_PATTERNS    = re.compile(r"\b(list|all|show|how many|count|what .* in)\b", re.I)
_PATH_PATTERNS    = re.compile(r"\b(path|route|from .* to|trace|flow)\b", re.I)
_IMPACT_PATTERNS  = re.compile(r"\b(impact|fail|isolat|trip|what happen|affect|downstream of)\b", re.I)
_SOP_PATTERNS     = re.compile(r"\b(sop|procedure|manual|how to|startup|shutdown|isolation|step)\b", re.I)
_DETAIL_PATTERNS  = re.compile(r"\b(what is|tell me about|describe|detail|info|about)\b", re.I)


def classify_query(question: str) -> str:
    if _PATH_PATTERNS.search(question):    return "path"
    if _IMPACT_PATTERNS.search(question):  return "impact"
    if _SOP_PATTERNS.search(question):     return "sop"
    if _LIST_PATTERNS.search(question):    return "list"
    if _DETAIL_PATTERNS.search(question):  return "detail"
    return "general"


# ── Tool builder (unit-scoped per request) ─────────────────────────────────────

def build_tools(graph_agent: GraphAgent, doc_agent: DocumentAgent,
                incident_agent: IncidentAgent, pid_agent: PIDAgent,
                unit_name: str):

    @tool
    def search_equipment(tag: str) -> str:
        """Search for a specific equipment tag (e.g. P-101, TIC-301). Returns connections and type."""
        result = graph_agent.search_equipment(tag)
        if not result["found"]:
            return f"Tag '{tag}' not found in unit {unit_name}."
        up   = ", ".join(result["upstream"])  or "none"
        down = ", ".join(result["downstream"]) or "none"
        return (
            f"Tag: {result['tag']} | Type: {result['tag_type']} | "
            f"Description: {result['description']}\n"
            f"Upstream: {up}\nDownstream: {down}"
        )

    @tool
    def list_by_type(equipment_type: str) -> str:
        """List all equipment of a given type in the current unit.
        Valid types: pump, vessel, valve, instrument, exchanger, compressor, line."""
        result = graph_agent.list_by_type(equipment_type)
        if result["count"] == 0:
            return f"No {equipment_type}s found in unit {unit_name}."
        return f"{result['count']} {equipment_type}(s) in {unit_name}: {', '.join(result['tags'])}"

    @tool
    def trace_process_path(source_tag: str, target_tag: str) -> str:
        """Trace the process flow path from source_tag to target_tag."""
        result = graph_agent.trace_path(source_tag, target_tag)
        if not result["found"]:
            return f"No process path found from {source_tag} to {target_tag}."
        path_str = " → ".join(result["path"])
        return f"Process path ({result['length']} steps): {path_str}"

    @tool
    def analyze_impact(tag: str) -> str:
        """Determine which equipment is affected downstream if a tag fails or is isolated."""
        result = graph_agent.analyze_impact(tag)
        if not result["found"]:
            return f"Tag '{tag}' not found in unit {unit_name}."
        if result["affected_count"] == 0:
            return f"{tag} has no downstream equipment — isolation has no further impact."
        by_type = result.get("affected_by_type", {})
        lines = [f"Severity: {result['severity'].upper()} — {result['affected_count']} affected equipment"]
        for typ, tags in by_type.items():
            lines.append(f"  {typ.title()}s: {', '.join(tags)}")
        return "\n".join(lines)

    @tool
    def search_sop(query: str) -> str:
        """Search SOPs and manuals for operational procedures. Use for startup, shutdown,
        isolation, inspection, or any step-by-step procedure questions."""
        result = doc_agent.search_sop(query)
        if result["results_found"] == 0:
            return "No relevant SOP or manual section found. Check that documents have been uploaded and indexed."
        parts = []
        for r in result["results"]:
            src = f"[{r['source']} p.{r['page']}]" if r.get("page") else f"[{r['source']}]"
            parts.append(f"{src}\n{r['content']}")
        return "\n\n---\n".join(parts)

    @tool
    def find_pid_sheet(tag: str) -> str:
        """Find which P&ID drawing sheet a tag comes from. Useful for citing sources."""
        result = pid_agent.get_tag_provenance(tag, unit_name)
        if not result["found"]:
            return f"No P&ID sheet record found for tag '{tag}'."
        return (
            f"Tag {result['tag']} ({result['tag_type']}) found on "
            f"{result['source_document']} page {result['page_number']}. "
            f"Description: {result['description']}"
        )

    @tool
    def find_incidents(tag: str) -> str:
        """Find past incidents related to a specific equipment tag."""
        result = incident_agent.find_related_incidents(tag, unit_name)
        if result["incidents_found"] == 0:
            return f"No recorded incidents found for tag '{tag}'."
        lines = [f"{result['incidents_found']} incident(s) involving {tag}:"]
        for inc in result["incidents"]:
            lines.append(f"  [{inc['severity'].upper()}] {inc['title']} — {inc['status']}")
        return "\n".join(lines)

    return [
        search_equipment,
        list_by_type,
        trace_process_path,
        analyze_impact,
        search_sop,
        find_pid_sheet,
        find_incidents,
    ]


# ── Coordinator Agent ──────────────────────────────────────────────────────────

class CoordinatorAgent:
    def __init__(self, graph: GraphBuilder, rag: RAGEngine):
        self.graph = graph
        self.rag = rag
        self.settings = get_settings()
        self._llm: ChatOllama | None = None

    def _get_llm(self) -> ChatOllama:
        if self._llm is None:
            self._llm = ChatOllama(
                base_url=self.settings.ollama_base_url,
                model=self.settings.ollama_chat_model,
                temperature=0,
            )
        return self._llm

    def _format_chat_history(self, chat_history: list[dict]) -> list:
        messages = []
        for msg in chat_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        return messages

    def run(self, question: str, unit_name: str, chat_history: list[dict] | None = None) -> dict:
        """
        Synchronous entry point — run in asyncio.to_thread() from async routes.
        Returns: {answer, query_type, sources, success}
        """
        chat_history = chat_history or []
        query_type = classify_query(question)

        # Build unit-scoped specialists
        graph_agent    = GraphAgent(self.graph, unit_name)
        doc_agent      = DocumentAgent(self.rag, unit_name)
        incident_agent = IncidentAgent()
        pid_agent      = PIDAgent()

        tools = build_tools(graph_agent, doc_agent, incident_agent, pid_agent, unit_name)
        llm   = self._get_llm()

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT + f"\n\nCurrent unit: **{unit_name}**"),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        agent    = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            max_iterations=6,
            return_intermediate_steps=True,
        )

        try:
            result = executor.invoke({
                "input": question,
                "chat_history": self._format_chat_history(chat_history),
            })

            # Extract sources from intermediate tool steps
            sources = _extract_sources(result.get("intermediate_steps", []))

            return {
                "answer":     result["output"],
                "query_type": query_type,
                "sources":    sources,
                "success":    True,
            }

        except Exception as exc:
            logger.error(f"CoordinatorAgent error for unit={unit_name}: {exc}")
            return {
                "answer":     f"I couldn't complete that query: {exc}",
                "query_type": query_type,
                "sources":    [],
                "success":    False,
            }


def _extract_sources(intermediate_steps: list) -> list[dict]:
    """
    Scan agent intermediate steps for tool calls that returned source info
    (find_pid_sheet, search_sop). Return de-duplicated source list.
    """
    sources = []
    seen = set()

    for action, observation in intermediate_steps:
        tool_name = getattr(action, "tool", "")

        if tool_name == "find_pid_sheet" and isinstance(observation, str):
            # Extract "filename page N" pattern
            match = re.search(r"on (.+?) page (\d+)", observation)
            if match:
                key = match.group(0)
                if key not in seen:
                    seen.add(key)
                    sources.append({"source": match.group(1), "page": match.group(2)})

        elif tool_name == "search_sop" and isinstance(observation, str):
            # Extract [filename p.N] patterns
            for m in re.finditer(r"\[(.+?) p\.(\d+)\]", observation):
                key = m.group(0)
                if key not in seen:
                    seen.add(key)
                    sources.append({"source": m.group(1), "page": m.group(2)})

    return sources
