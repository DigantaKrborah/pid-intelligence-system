from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_ollama import OllamaEmbeddings
from loguru import logger

from backend.config import get_settings


class RAGEngine:
    """ChromaDB-backed retrieval engine. Per-unit collections for equipment and documents."""

    def __init__(self):
        self.settings = get_settings()
        self.client = chromadb.PersistentClient(
            path=self.settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.embeddings = OllamaEmbeddings(
            base_url=self.settings.ollama_base_url,
            model=self.settings.ollama_embed_model,
        )

    def _collection_name(self, unit_name: str, kind: str) -> str:
        return f"{unit_name.lower()}_{kind}"

    def _get_or_create(self, collection_name: str):
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def index_equipment(self, unit_name: str, tags: list[dict]) -> None:
        """Index equipment tag descriptions for semantic search."""
        collection = self._get_or_create(self._collection_name(unit_name, "equipment"))
        texts = [
            f"{t['tag']} — {t.get('tag_type', '')} — {t.get('description', '')}"
            for t in tags
        ]
        embeddings = self.embeddings.embed_documents(texts)
        collection.upsert(
            ids=[t["tag"] for t in tags],
            embeddings=embeddings,
            documents=texts,
            metadatas=[{"tag_type": t.get("tag_type", ""), "unit": unit_name} for t in tags],
        )
        logger.info(f"Indexed {len(tags)} equipment tags for unit {unit_name}")

    def index_document_chunks(self, unit_name: str, chunks: list[dict]) -> None:
        """Index SOP/manual text chunks. Each chunk: {id, content, source, page}."""
        collection = self._get_or_create(self._collection_name(unit_name, "docs"))
        texts = [c["content"] for c in chunks]
        embeddings = self.embeddings.embed_documents(texts)
        collection.upsert(
            ids=[c["id"] for c in chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[{"source": c["source"], "page": c.get("page", 0)} for c in chunks],
        )
        logger.info(f"Indexed {len(chunks)} document chunks for unit {unit_name}")

    def search_equipment(
        self, query: str, unit_name: str, n_results: int = 10
    ) -> list[dict]:
        collection = self._get_or_create(self._collection_name(unit_name, "equipment"))
        embedding = self.embeddings.embed_query(query)
        results = collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, collection.count() or 1),
        )
        items = []
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            items.append({"content": doc, "metadata": meta, "score": 1 - dist})
        return items

    def search_documents(
        self, query: str, unit_name: str, n_results: int = 3
    ) -> list[dict]:
        collection = self._get_or_create(self._collection_name(unit_name, "docs"))
        if collection.count() == 0:
            return []
        embedding = self.embeddings.embed_query(query)
        results = collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, collection.count()),
        )
        items = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            items.append({"content": doc, "source": meta.get("source", ""), "page": meta.get("page")})
        return items

    def get_collection_stats(self, unit_name: str) -> dict:
        """Return count of indexed items per collection for a unit."""
        equip_col = self._get_or_create(self._collection_name(unit_name, "equipment"))
        docs_col = self._get_or_create(self._collection_name(unit_name, "docs"))
        return {
            "unit": unit_name,
            "equipment_indexed": equip_col.count(),
            "doc_chunks_indexed": docs_col.count(),
        }

    def delete_tags(self, unit_name: str, tag_ids: list[str]) -> None:
        """Remove specific tag embeddings from the equipment collection."""
        if not tag_ids:
            return
        try:
            collection = self._get_or_create(self._collection_name(unit_name, "equipment"))
            collection.delete(ids=tag_ids)
            logger.info(f"Deleted {len(tag_ids)} tag embeddings for unit {unit_name}")
        except Exception as exc:
            logger.warning(f"ChromaDB delete_tags failed (non-fatal): {exc}")

    def delete_unit_collections(self, unit_name: str) -> None:
        """Remove all ChromaDB collections for a unit (called on archive)."""
        for kind in ("equipment", "docs"):
            name = self._collection_name(unit_name, kind)
            try:
                self.client.delete_collection(name)
                logger.info(f"Deleted ChromaDB collection: {name}")
            except Exception:
                pass  # Collection may not exist yet
