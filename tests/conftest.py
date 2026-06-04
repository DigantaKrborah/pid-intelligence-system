"""
conftest.py — shared fixtures for all tests.

Heavy optional deps (langchain, chromadb, google-generativeai, pdf2image) are
stubbed at the sys.modules level so unit tests can run without a full install.
CI installs everything from requirements.txt, so integration tests get the real libs.
"""
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient


# ── Stub heavy deps that are not required for unit tests ──────────────────────

def _stub(name: str, **attrs):
    """Register a minimal stub module so imports don't fail."""
    if name not in sys.modules:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod
    return sys.modules[name]


# LangChain family
_stub("langchain")
_stub("langchain.agents",                    AgentExecutor=MagicMock, create_tool_calling_agent=MagicMock)
_stub("langchain_core")
_stub("langchain_core.prompts",              ChatPromptTemplate=MagicMock, MessagesPlaceholder=MagicMock)
_stub("langchain_core.tools",                tool=lambda f: f)
_stub("langchain_core.messages",             HumanMessage=MagicMock, AIMessage=MagicMock)
_stub("langchain_ollama",                    ChatOllama=MagicMock, OllamaEmbeddings=MagicMock)
_stub("langchain_community")
_stub("langchain_google_genai")

# Google Generative AI
_stub("google")
_stub("google.generativeai",                 configure=MagicMock, GenerativeModel=MagicMock)

# ChromaDB
_chroma_settings = MagicMock()
_stub("chromadb",                            PersistentClient=MagicMock)
_stub("chromadb.config",                     Settings=MagicMock)

# PDF / Vision deps
_stub("pdf2image",                           convert_from_path=MagicMock)
_stub("pypdf",                               PdfReader=MagicMock)
_stub("docx",                                Document=MagicMock)
_stub("cv2")
_stub("PIL")
_stub("PIL.Image")

# GitHub
_stub("github",                              Github=MagicMock)

# psycopg2 (used by incident/pid agents in sync SQL path)
_stub("psycopg2")


# ── Now import the app (all imports above must be stubbed first) ───────────────

from backend.main import app                         # noqa: E402
from backend.config import get_settings, Settings    # noqa: E402


# ── Settings fixture ───────────────────────────────────────────────────────────

@pytest.fixture
def test_settings():
    return Settings(
        app_env="test",
        gemini_api_key="test-key",
        database_url="postgresql+asyncpg://pid_user:test@localhost:5432/pid_test",
        chroma_persist_dir="./test_chroma_db",
        upload_dir="./test_data/pids",
        manuals_dir="./test_data/manuals",
        graph_dir="./test_data/graphs",
        github_token="",
        github_repo="",
    )


# ── DB mock ────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """A mock AsyncSession suitable for use as a FastAPI dependency override."""
    session = AsyncMock(spec=AsyncSession)

    # Default return values — tests can override per-case
    session.execute    = AsyncMock(return_value=_make_result([]))
    session.scalar     = AsyncMock(return_value=0)
    session.commit     = AsyncMock()
    session.rollback   = AsyncMock()
    session.flush      = AsyncMock()
    session.add        = MagicMock()
    session.delete     = AsyncMock()
    session.refresh    = AsyncMock()
    return session


def _make_result(rows):
    """Build a mock SQLAlchemy execute result from a list of objects."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = rows[0] if rows else None
    result.scalars.return_value.all.return_value = rows
    result.first.return_value = rows[0] if rows else None
    result.fetchall.return_value = rows
    return result


# ── TestClient fixture ─────────────────────────────────────────────────────────

@pytest.fixture
def client(test_settings, mock_db):
    from backend.db.database import get_db

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db] = override_db

    # Patch lifespan DB calls so startup doesn't need real postgres/ollama
    with patch("backend.main.init_db",                  new_callable=AsyncMock), \
         patch("backend.main.ensure_all_graphs_loaded",  new_callable=AsyncMock), \
         patch("backend.db.database.get_session_factory", return_value=MagicMock()):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    app.dependency_overrides.clear()


# ── Shared test data ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_extracted_tags():
    return [
        {"tag": "P-101", "tag_type": "pump",       "description": "Feed pump",                    "connected_to": ["V-101", "FCV-101"]},
        {"tag": "V-101", "tag_type": "vessel",     "description": "Feed drum",                    "connected_to": ["P-101", "LV-101"]},
        {"tag": "FCV-101","tag_type": "valve",     "description": "Feed control valve",           "connected_to": ["E-101"]},
        {"tag": "TIC-301","tag_type": "instrument","description": "Column top temp controller",   "connected_to": []},
    ]


@pytest.fixture
def sample_unit():
    unit = MagicMock()
    unit.id   = "11111111-1111-1111-1111-111111111111"
    unit.name = "CDU"
    unit.display_name = "Crude Distillation Unit"
    unit.description  = "Main crude distillation unit"
    unit.status       = "active"
    from datetime import datetime, timezone
    unit.created_at   = datetime.now(timezone.utc)
    unit.updated_at   = datetime.now(timezone.utc)
    return unit
