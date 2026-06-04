import pytest
import json
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path


@pytest.fixture
def extractor():
    with patch("backend.vision.extractor.genai") as mock_genai, \
         patch("backend.vision.extractor.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = "test-key"
        mock_settings.return_value.gemini_vision_model = "gemini-1.5-flash"
        from backend.vision.extractor import PIDExtractor
        e = PIDExtractor()
        yield e, mock_genai


def test_extract_from_image_parses_json(extractor, tmp_path):
    e, mock_genai = extractor
    img_path = tmp_path / "page_001.png"
    img_path.write_bytes(b"fake-image-data")

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "tags": [
            {"tag": "P-101", "tag_type": "pump", "description": "Feed pump", "connected_to": ["V-101"]},
        ],
        "sheet_number": "P&ID-CDU-001",
        "process_description": "CDU feed section",
    })
    e.model.generate_content = MagicMock(return_value=mock_response)

    result = e.extract_from_image(img_path)
    assert len(result["tags"]) == 1
    assert result["tags"][0]["tag"] == "P-101"
    assert result["sheet_number"] == "P&ID-CDU-001"


def test_extract_from_image_handles_markdown_fence(extractor, tmp_path):
    e, mock_genai = extractor
    img_path = tmp_path / "page_001.png"
    img_path.write_bytes(b"fake-image-data")

    mock_response = MagicMock()
    mock_response.text = "```json\n{\"tags\": [], \"sheet_number\": \"S1\", \"process_description\": \"\"}\n```"
    e.model.generate_content = MagicMock(return_value=mock_response)

    result = e.extract_from_image(img_path)
    assert result["tags"] == []


def test_extract_from_image_handles_bad_json(extractor, tmp_path):
    e, _ = extractor
    img_path = tmp_path / "page_001.png"
    img_path.write_bytes(b"fake-image-data")

    mock_response = MagicMock()
    mock_response.text = "Not valid JSON at all"
    e.model.generate_content = MagicMock(return_value=mock_response)

    result = e.extract_from_image(img_path)
    assert result["tags"] == []
    assert "sheet_number" in result
