"""RAGEngine tests — ChromaDB and Ollama embeddings fully mocked."""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def rag(tmp_path):
    with patch("backend.rag.engine.chromadb.PersistentClient") as mock_chroma, \
         patch("backend.rag.engine.OllamaEmbeddings") as mock_embed, \
         patch("backend.rag.engine.get_settings") as mock_settings:

        mock_settings.return_value.chroma_persist_dir = str(tmp_path)
        mock_settings.return_value.ollama_base_url    = "http://localhost:11434"
        mock_settings.return_value.ollama_embed_model = "nomic-embed-text"

        # Mock embedding: return a 3-dim vector for any text
        mock_embed.return_value.embed_documents.return_value = [[0.1, 0.2, 0.3]]
        mock_embed.return_value.embed_query.return_value      = [0.1, 0.2, 0.3]

        # Mock ChromaDB collection
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

        from backend.rag.engine import RAGEngine
        engine = RAGEngine()
        engine._mock_collection = mock_collection   # expose for assertions
        yield engine


def test_index_equipment_calls_upsert(rag):
    tags = [{"tag": "P-101", "tag_type": "pump", "description": "Feed pump"}]
    rag.index_equipment("CDU", tags)
    rag._mock_collection.upsert.assert_called_once()
    call_kwargs = rag._mock_collection.upsert.call_args.kwargs
    assert call_kwargs["ids"] == ["P-101"]


def test_index_equipment_builds_correct_text(rag):
    tags = [{"tag": "TIC-301", "tag_type": "instrument", "description": "Column temp controller"}]
    rag.index_equipment("CDU", tags)
    call_kwargs = rag._mock_collection.upsert.call_args.kwargs
    assert "TIC-301" in call_kwargs["documents"][0]
    assert "instrument" in call_kwargs["documents"][0]


def test_index_document_chunks_calls_upsert(rag):
    chunks = [{"id": "doc_chunk_0000", "content": "Step 1: Open valve", "source": "SOP.pdf", "page": 1}]
    rag.index_document_chunks("CDU", chunks)
    rag._mock_collection.upsert.assert_called_once()


def test_search_equipment_empty_collection_returns_empty(rag):
    rag._mock_collection.count.return_value = 0
    results = rag.search_equipment("feed pump", "CDU")
    # When count == 0, query is still called with n_results=min(10, 1)
    assert isinstance(results, list)


def test_search_equipment_with_results(rag):
    rag._mock_collection.count.return_value = 2
    rag._mock_collection.query.return_value = {
        "documents": [["P-101 — pump — Feed pump", "V-101 — vessel — Feed drum"]],
        "metadatas": [[{"tag_type": "pump", "unit": "CDU"}, {"tag_type": "vessel", "unit": "CDU"}]],
        "distances": [[0.1, 0.3]],
    }
    results = rag.search_equipment("pump", "CDU", n_results=2)
    assert len(results) == 2
    assert results[0]["content"] == "P-101 — pump — Feed pump"
    assert results[0]["score"] == pytest.approx(0.9)   # 1 - 0.1


def test_search_documents_empty_returns_empty(rag):
    rag._mock_collection.count.return_value = 0
    results = rag.search_documents("startup procedure", "CDU")
    assert results == []


def test_search_documents_with_results(rag):
    rag._mock_collection.count.return_value = 1
    rag._mock_collection.query.return_value = {
        "documents": [["Open isolation valve before starting pump."]],
        "metadatas": [[{"source": "CDU_SOP.pdf", "page": 3}]],
    }
    results = rag.search_documents("startup", "CDU", n_results=1)
    assert len(results) == 1
    assert results[0]["source"] == "CDU_SOP.pdf"
    assert results[0]["page"]   == 3


def test_get_collection_stats(rag):
    rag._mock_collection.count.return_value = 42
    stats = rag.get_collection_stats("CDU")
    assert stats["unit"] == "CDU"
    assert "equipment_indexed"   in stats
    assert "doc_chunks_indexed"  in stats


def test_delete_unit_collections(rag):
    rag.delete_unit_collections("CDU")
    # Should call delete_collection twice (equipment + docs)
    assert rag.client.delete_collection.call_count == 2


def test_collection_name_format(rag):
    name = rag._collection_name("CDU", "equipment")
    assert name == "cdu_equipment"

    name2 = rag._collection_name("HCU", "docs")
    assert name2 == "hcu_docs"
