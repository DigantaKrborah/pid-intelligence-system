import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_doc():
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.filename = "test_pid.pdf"
    doc.file_path = "/tmp/test_pid.pdf"
    doc.processing_status = "queued"
    return doc


@pytest.fixture
def mock_unit():
    unit = MagicMock()
    unit.id = uuid.uuid4()
    unit.name = "CDU"
    return unit


@pytest.fixture
def sample_page_result():
    return {
        "page_number": 1,
        "sheet_number": "P&ID-CDU-001",
        "process_description": "CDU feed section",
        "tags": [
            {"tag": "P-101", "tag_type": "pump", "description": "Feed pump", "connected_to": ["V-101", "FCV-101"]},
            {"tag": "V-101", "tag_type": "vessel", "description": "Feed drum", "connected_to": ["P-101"]},
            {"tag": "FCV-101", "tag_type": "valve", "description": "Feed control valve", "connected_to": []},
        ],
    }


@pytest.mark.asyncio
async def test_process_pid_document_success(mock_doc, mock_unit, sample_page_result):
    """Full pipeline: extraction → DB upsert → graph save → ChromaDB index."""
    with patch("backend.services.processing.get_session_factory") as mock_factory, \
         patch("backend.services.processing.asyncio.to_thread") as mock_thread, \
         patch("backend.services.processing._graph_builder") as mock_graph, \
         patch("backend.services.processing._index_in_chromadb") as mock_chroma:

        # Set up session mock
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_factory.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.return_value.__aexit__ = AsyncMock(return_value=False)

        # Mock repositories
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_document.return_value = mock_doc
        mock_doc_repo.create_processing_job.return_value = MagicMock(id=uuid.uuid4())
        mock_doc_repo.upsert_tag.return_value = MagicMock(id=uuid.uuid4())

        mock_unit_repo = AsyncMock()
        mock_unit_repo.get_by_id.return_value = mock_unit

        # Extraction returns one page
        mock_thread.return_value = [sample_page_result]
        mock_chroma.return_value = None

        with patch("backend.services.processing.DocumentRepository", return_value=mock_doc_repo), \
             patch("backend.services.processing.UnitRepository", return_value=mock_unit_repo):
            from backend.services.processing import process_pid_document
            await process_pid_document(mock_doc.id, mock_unit.id)

        # Verify status was updated to completed
        status_calls = [call.args[1] for call in mock_doc_repo.update_status.call_args_list]
        assert "completed" in status_calls

        # Verify graph nodes were added for all 3 tags
        assert mock_graph.add_equipment.call_count == 3

        # Verify graph was saved
        mock_graph.save.assert_called_once_with("CDU")


@pytest.mark.asyncio
async def test_process_pid_document_marks_failed_on_exception(mock_doc, mock_unit):
    """If extraction raises, document status is set to failed."""
    with patch("backend.services.processing.get_session_factory") as mock_factory, \
         patch("backend.services.processing.asyncio.to_thread", side_effect=RuntimeError("Gemini error")):

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_factory.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_document.return_value = mock_doc
        mock_doc_repo.create_processing_job.return_value = MagicMock(id=uuid.uuid4())

        mock_unit_repo = AsyncMock()
        mock_unit_repo.get_by_id.return_value = mock_unit

        with patch("backend.services.processing.DocumentRepository", return_value=mock_doc_repo), \
             patch("backend.services.processing.UnitRepository", return_value=mock_unit_repo):
            from backend.services.processing import process_pid_document
            await process_pid_document(mock_doc.id, mock_unit.id)

        status_calls = [call.args[1] for call in mock_doc_repo.update_status.call_args_list]
        assert "failed" in status_calls


@pytest.mark.asyncio
async def test_process_pid_document_skips_empty_tags(mock_doc, mock_unit):
    """Pages with empty tag lists are processed without errors."""
    page_with_no_tags = {"page_number": 1, "tags": [], "sheet_number": "S1", "process_description": ""}

    with patch("backend.services.processing.get_session_factory") as mock_factory, \
         patch("backend.services.processing.asyncio.to_thread", return_value=[page_with_no_tags]), \
         patch("backend.services.processing._graph_builder") as mock_graph, \
         patch("backend.services.processing._index_in_chromadb", return_value=None):

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_factory.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_document.return_value = mock_doc
        mock_doc_repo.create_processing_job.return_value = MagicMock(id=uuid.uuid4())

        mock_unit_repo = AsyncMock()
        mock_unit_repo.get_by_id.return_value = mock_unit

        with patch("backend.services.processing.DocumentRepository", return_value=mock_doc_repo), \
             patch("backend.services.processing.UnitRepository", return_value=mock_unit_repo):
            from backend.services.processing import process_pid_document
            await process_pid_document(mock_doc.id, mock_unit.id)

        mock_graph.add_equipment.assert_not_called()
        status_calls = [call.args[1] for call in mock_doc_repo.update_status.call_args_list]
        assert "completed" in status_calls
