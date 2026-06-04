import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from backend.main import app
from backend.config import get_settings, Settings


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


@pytest.fixture
def client(test_settings):
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_extracted_tags():
    return [
        {"tag": "P-101", "tag_type": "pump", "description": "Feed pump", "connected_to": ["V-101", "FCV-101"]},
        {"tag": "V-101", "tag_type": "vessel", "description": "Feed drum", "connected_to": ["P-101", "LV-101"]},
        {"tag": "FCV-101", "tag_type": "valve", "description": "Feed control valve", "connected_to": ["E-101"]},
        {"tag": "TIC-301", "tag_type": "instrument", "description": "Column top temperature controller", "connected_to": []},
    ]
