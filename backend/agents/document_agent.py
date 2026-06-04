"""
Document Agent — specialist for SOP and manual retrieval via ChromaDB.
"""
from backend.rag.engine import RAGEngine


class DocumentAgent:
    def __init__(self, rag: RAGEngine, unit_name: str):
        self.rag = rag
        self.unit_name = unit_name

    def search_sop(self, query: str, n_results: int = 3) -> dict:
        """Semantic search over indexed SOP and manual chunks."""
        hits = self.rag.search_documents(query, self.unit_name, n_results=n_results)
        return {
            "query": query,
            "unit": self.unit_name,
            "results_found": len(hits),
            "results": [
                {
                    "content": h["content"],
                    "source": h.get("source", ""),
                    "page": h.get("page"),
                }
                for h in hits
            ],
        }

    def search_equipment_semantic(self, query: str, n_results: int = 10) -> dict:
        """Semantic search over equipment descriptions in ChromaDB."""
        hits = self.rag.search_equipment(query, self.unit_name, n_results=n_results)
        tags = []
        for h in hits:
            parts = h["content"].split(" — ", 2)
            tags.append({
                "tag": parts[0].strip() if parts else "",
                "tag_type": parts[1].strip() if len(parts) > 1 else "",
                "description": parts[2].strip() if len(parts) > 2 else "",
                "score": h.get("score", 0.0),
            })
        return {
            "query": query,
            "unit": self.unit_name,
            "results": tags,
        }

    def get_collection_stats(self) -> dict:
        """Return ChromaDB index stats for the current unit."""
        return self.rag.get_collection_stats(self.unit_name)
