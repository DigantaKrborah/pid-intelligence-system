from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from loguru import logger

from backend.config import get_settings
from backend.graph.builder import GraphBuilder
from backend.rag.engine import RAGEngine


SYSTEM_PROMPT = """You are an expert P&ID (Piping & Instrumentation Diagram) engineering assistant.
You help process engineers at refineries and chemical plants understand their process equipment,
trace process paths, and retrieve operational procedures.

You have access to tools for:
- Searching equipment tags in the knowledge graph
- Tracing process paths between equipment
- Listing equipment by type
- Finding impact of equipment failures
- Retrieving SOP and manual information

Always cite the source P&ID sheet or document when providing answers.
Be concise and technical. Use engineering terminology.
"""


def build_tools(graph: GraphBuilder, rag: RAGEngine, unit_name: str):
    @tool
    def search_equipment(tag: str) -> str:
        """Search for a specific equipment tag and return its details and connections."""
        neighbours = graph.get_neighbours(unit_name, tag)
        return f"Tag: {tag}\nUpstream: {neighbours['upstream']}\nDownstream: {neighbours['downstream']}"

    @tool
    def list_equipment_by_type(equipment_type: str) -> str:
        """List all equipment of a given type in the current unit. Types: pump, vessel, valve, instrument, exchanger."""
        items = graph.get_nodes_by_type(unit_name, equipment_type)
        if not items:
            return f"No {equipment_type} found in unit {unit_name}."
        tags = [item["tag"] for item in items]
        return f"{equipment_type.title()}s in {unit_name}: {', '.join(tags)}"

    @tool
    def trace_process_path(source_tag: str, target_tag: str) -> str:
        """Trace the process path between two equipment tags."""
        path = graph.find_path(unit_name, source_tag, target_tag)
        if path is None:
            return f"No path found from {source_tag} to {target_tag}."
        return f"Process path: {' → '.join(path)}"

    @tool
    def find_impact(tag: str) -> str:
        """Find what equipment is affected if a given tag is isolated or fails."""
        neighbours = graph.get_neighbours(unit_name, tag, depth=3)
        downstream = neighbours.get("downstream", [])
        if not downstream:
            return f"No downstream impact found for {tag}."
        return f"If {tag} fails, affected downstream equipment: {', '.join(downstream)}"

    @tool
    def search_sop(query: str) -> str:
        """Search SOPs and manuals for operational procedures related to a query."""
        results = rag.search_documents(query, unit_name=unit_name, n_results=3)
        if not results:
            return "No relevant SOP or manual found."
        return "\n\n".join(
            f"Source: {r['source']}\n{r['content']}" for r in results
        )

    return [search_equipment, list_equipment_by_type, trace_process_path, find_impact, search_sop]


class CoordinatorAgent:
    def __init__(self, graph: GraphBuilder, rag: RAGEngine):
        self.graph = graph
        self.rag = rag
        self.settings = get_settings()

    def run(self, question: str, unit_name: str, chat_history: list = []) -> dict:
        llm = ChatOllama(
            base_url=self.settings.ollama_base_url,
            model=self.settings.ollama_chat_model,
        )
        tools = build_tools(self.graph, self.rag, unit_name)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT + f"\n\nCurrent unit: {unit_name}"),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=5)

        try:
            result = executor.invoke({"input": question, "chat_history": chat_history})
            return {"answer": result["output"], "success": True}
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return {"answer": f"I couldn't answer that question: {e}", "success": False}
