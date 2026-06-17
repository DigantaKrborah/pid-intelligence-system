"""
test_extraction.py — Unit tests for LLM response parsing logic in LLMService.

These tests do NOT make any live API calls. They test the parsing functions
(parse_llm_response, parse_json_array_response) using canned LLM output strings,
and they test that extract_from_image raises correctly when the image is missing.

Run with pytest (from the backend/ directory):
    python -m pytest tests/test_extraction.py -v

Or run directly:
    python tests/test_extraction.py
"""

import sys
import json
import pathlib
import pytest

# Allow running from the backend/ directory directly
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from app.services.llm_service import LLMService

svc = LLMService()

# ── Sample fixtures ────────────────────────────────────────────────────────────

VALID_EXTRACTION_RESPONSE = json.dumps({
    "equipment_tags": [
        {
            "tag_number": "P-101A",
            "tag_type": "PUMP",
            "description": "Crude Charge Pump",
            "service": "Crude oil transfer",
            "design_pressure": "50 kg/cm2g",
            "design_temp": "150°C",
            "capacity": "200 m3/hr",
            "material": "CS",
            "notes": "",
        },
        {
            "tag_number": "E-201",
            "tag_type": "HEAT_EXCHANGER",
            "description": "Crude Pre-Heater",
            "service": "Crude preheat",
            "design_pressure": "40 kg/cm2g",
            "design_temp": "200°C",
            "capacity": "",
            "material": "SS316",
            "notes": "",
        },
    ],
    "instrument_tags": [
        {
            "tag_number": "FIC-1001",
            "instrument_type": "FIC",
            "description": "Feed Flow Controller",
            "process_variable": "FLOW",
            "service": "Crude feed flow control",
            "range_low": "0",
            "range_high": "500",
            "unit_of_measure": "m3/hr",
            "notes": "",
        },
    ],
    "line_specs": [
        {
            "line_number": '6"-HN-1001-150#-A1A',
            "nominal_diameter": '6"',
            "fluid_service": "HN",
            "line_sequence": "1001",
            "pressure_class": "150#",
            "pipe_spec": "A1A",
            "insulation_code": "",
            "tracing_code": "",
            "from_equipment": "P-101A",
            "to_equipment": "E-201",
            "notes": "",
        },
    ],
    "drawing_references": [],
    "connectivity": [
        {
            "source_tag": "P-101A",
            "source_tag_type": "EQUIPMENT",
            "target_tag": "E-201",
            "target_tag_type": "EQUIPMENT",
            "direction": "DOWNSTREAM",
            "via_line": '6"-HN-1001-150#-A1A',
        },
    ],
    "extraction_confidence": "HIGH",
    "extraction_notes": "Sample test extraction — no actual image analysed.",
})

MARKDOWN_WRAPPED_RESPONSE = f"```json\n{VALID_EXTRACTION_RESPONSE}\n```"

MARKDOWN_NO_LANGUAGE_RESPONSE = f"```\n{VALID_EXTRACTION_RESPONSE}\n```"

RESPONSE_WITH_PREAMBLE = (
    "Here is the extracted JSON as requested:\n\n"
    f"{VALID_EXTRACTION_RESPONSE}\n\nLet me know if you need anything else."
)

VALID_ARRAY_RESPONSE = json.dumps([
    {"chunk_text": "The crude distillation unit operates at atmospheric pressure.", "page": 1, "tags": ["CDU", "P-101A"]},
    {"chunk_text": "Feed enters through P-101A at 200 m3/hr.", "page": 1, "tags": ["P-101A", "FIC-1001"]},
])

ARRAY_MARKDOWN_WRAPPED = f"```json\n{VALID_ARRAY_RESPONSE}\n```"


# ── parse_llm_response ─────────────────────────────────────────────────────────

def test_parse_clean_json():
    """parse_llm_response handles perfect JSON output."""
    result = svc.parse_llm_response(VALID_EXTRACTION_RESPONSE)
    assert isinstance(result, dict)
    assert "equipment_tags" in result
    assert len(result["equipment_tags"]) == 2
    assert result["equipment_tags"][0]["tag_number"] == "P-101A"
    assert result["extraction_confidence"] == "HIGH"
    print(f"\n  ✓ Clean JSON: {len(result['equipment_tags'])} equipment, {len(result['instrument_tags'])} instruments")


def test_parse_markdown_code_block():
    """parse_llm_response strips ```json ... ``` code fences."""
    result = svc.parse_llm_response(MARKDOWN_WRAPPED_RESPONSE)
    assert isinstance(result, dict)
    assert "equipment_tags" in result
    print(f"\n  ✓ Markdown ```json``` stripped correctly")


def test_parse_markdown_no_language():
    """parse_llm_response strips ``` ... ``` code fences with no language tag."""
    result = svc.parse_llm_response(MARKDOWN_NO_LANGUAGE_RESPONSE)
    assert isinstance(result, dict)
    assert "equipment_tags" in result
    print(f"\n  ✓ Markdown ``` (no lang) stripped correctly")


def test_parse_response_with_preamble():
    """parse_llm_response extracts the JSON block when there's surrounding text."""
    result = svc.parse_llm_response(RESPONSE_WITH_PREAMBLE)
    assert isinstance(result, dict)
    assert "equipment_tags" in result
    print(f"\n  ✓ JSON extracted from response with preamble text")


def test_parse_empty_response_raises():
    """parse_llm_response raises ValueError on empty or whitespace input."""
    with pytest.raises(ValueError, match="empty response"):
        svc.parse_llm_response("")
    with pytest.raises(ValueError, match="empty response"):
        svc.parse_llm_response("   \n  ")
    print(f"\n  ✓ Empty input raises ValueError")


def test_parse_garbage_raises():
    """parse_llm_response raises ValueError when input cannot be parsed as JSON."""
    with pytest.raises(ValueError, match="Could not parse"):
        svc.parse_llm_response("This is just a plain text sentence. No JSON here.")
    print(f"\n  ✓ Non-JSON text raises ValueError")


def test_parse_partial_json_raises():
    """parse_llm_response raises ValueError on truncated JSON."""
    truncated = '{"equipment_tags": [{"tag_number": "P-101A"'   # deliberately cut off
    with pytest.raises(ValueError):
        svc.parse_llm_response(truncated)
    print(f"\n  ✓ Truncated JSON raises ValueError")


def test_parse_equipment_tags_structure():
    """Verify the extracted equipment tag structure has all expected keys."""
    result = svc.parse_llm_response(VALID_EXTRACTION_RESPONSE)
    required_keys = {"tag_number", "tag_type", "description", "service", "material"}
    for tag in result["equipment_tags"]:
        missing = required_keys - tag.keys()
        assert not missing, f"Equipment tag missing keys: {missing} in {tag}"
    print(f"\n  ✓ All equipment tags have required keys")


def test_parse_instrument_tags_structure():
    """Verify the extracted instrument tag structure has all expected keys."""
    result = svc.parse_llm_response(VALID_EXTRACTION_RESPONSE)
    required_keys = {"tag_number", "instrument_type", "description", "process_variable"}
    for tag in result["instrument_tags"]:
        missing = required_keys - tag.keys()
        assert not missing, f"Instrument tag missing keys: {missing} in {tag}"
    print(f"\n  ✓ All instrument tags have required keys")


def test_parse_connectivity_structure():
    """Verify connectivity entries have source/target fields."""
    result = svc.parse_llm_response(VALID_EXTRACTION_RESPONSE)
    for conn in result["connectivity"]:
        assert "source_tag" in conn
        assert "target_tag" in conn
        assert "direction" in conn
    print(f"\n  ✓ Connectivity entries have required fields")


def test_parse_confidence_field():
    """extraction_confidence should be HIGH, MEDIUM, or LOW."""
    result = svc.parse_llm_response(VALID_EXTRACTION_RESPONSE)
    assert result["extraction_confidence"] in {"HIGH", "MEDIUM", "LOW"}
    print(f"\n  ✓ extraction_confidence value is valid: {result['extraction_confidence']}")


# ── parse_json_array_response ──────────────────────────────────────────────────

def test_parse_array_clean():
    """parse_json_array_response handles clean JSON array."""
    result = svc.parse_json_array_response(VALID_ARRAY_RESPONSE)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["page"] == 1
    print(f"\n  ✓ Clean array: {len(result)} chunk(s)")


def test_parse_array_markdown_wrapped():
    """parse_json_array_response strips ```json ... ``` from array responses."""
    result = svc.parse_json_array_response(ARRAY_MARKDOWN_WRAPPED)
    assert isinstance(result, list)
    assert len(result) == 2
    print(f"\n  ✓ Array markdown stripped: {len(result)} chunk(s)")


def test_parse_array_empty_input_returns_empty():
    """parse_json_array_response returns [] on empty or blank input — never raises."""
    assert svc.parse_json_array_response("") == []
    assert svc.parse_json_array_response("   ") == []
    print(f"\n  ✓ Empty input returns []")


def test_parse_array_garbage_returns_empty():
    """parse_json_array_response returns [] (not raises) on unparseable input."""
    result = svc.parse_json_array_response("Summarise the document for me.")
    assert result == []
    print(f"\n  ✓ Non-JSON input returns []")


def test_parse_array_dict_input_returns_empty():
    """parse_json_array_response returns [] if the LLM returned a dict instead of an array."""
    result = svc.parse_json_array_response(VALID_EXTRACTION_RESPONSE)  # dict, not list
    assert result == []
    print(f"\n  ✓ Dict input returns [] (expected list)")


def test_parse_array_empty_array():
    """parse_json_array_response handles [] gracefully."""
    result = svc.parse_json_array_response("[]")
    assert result == []
    print(f"\n  ✓ Literal [] returns []")


# ── extract_from_image error handling ────────────────────────────────────────

def test_extract_missing_image_raises():
    """extract_from_image raises FileNotFoundError for a non-existent image path."""
    with pytest.raises(FileNotFoundError):
        svc.extract_from_image(
            image_path="/nonexistent/path/image_page_1.png",
            provider="claude",
            model_name="claude-opus-4-5",
            api_key="sk-test-fake",
            drawing_context={
                "unit_name": "CDU",
                "drawing_number": "CDU-PID-001",
                "drawing_title": "Crude Distillation Unit",
                "page_number": 1,
            },
        )
    print(f"\n  ✓ Missing image path raises FileNotFoundError (not RuntimeError)")


def test_extract_unknown_provider_raises():
    """extract_from_image raises ValueError for an unknown provider."""
    import tempfile, os
    # Create a tiny temp image file so the path check passes
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)  # minimal PNG header bytes
        tmp_path = f.name

    try:
        with pytest.raises(ValueError, match="Unknown provider"):
            svc.extract_from_image(
                image_path=tmp_path,
                provider="unknown_provider",
                model_name="some-model",
                api_key="sk-test-fake",
                drawing_context={
                    "unit_name": "CDU",
                    "drawing_number": "CDU-PID-001",
                    "drawing_title": "Crude Distillation Unit",
                    "page_number": 1,
                },
            )
    finally:
        os.unlink(tmp_path)

    print(f"\n  ✓ Unknown provider raises ValueError")


def test_get_provider_client_invalid_raises():
    """get_provider_client raises ValueError for unsupported provider names."""
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        svc.get_provider_client("fakecloud", "sk-test")
    print(f"\n  ✓ get_provider_client raises ValueError for unknown provider")


# ── Live extraction smoke test (skipped unless real image exists) ──────────────

def test_live_extract_skipped_no_image(tmp_path):
    """
    Smoke test: if uploads/ has any .png files, attempt extraction using
    the configured LLM provider. Skipped automatically when no images exist
    or when no LLM is configured (API key absent). This test never hard-fails
    on missing images — it uses pytest.skip().
    """
    import os

    # Look for any PNG in the uploads folder
    uploads_dir = pathlib.Path(__file__).parent.parent.parent / "data" / "pids"
    images = sorted(uploads_dir.glob("**/*.png")) if uploads_dir.exists() else []

    if not images:
        pytest.skip("No PNG images in data/pids/ — skipping live extraction smoke test")

    image = images[0]

    # Try to get settings from environment
    provider  = os.environ.get("LLM_PROVIDER")
    model     = os.environ.get("LLM_MODEL")
    api_key   = os.environ.get("LLM_API_KEY")

    if not provider or not api_key:
        pytest.skip(
            "LLM_PROVIDER and LLM_API_KEY env vars not set — "
            "skipping live extraction smoke test"
        )

    print(f"\n  Running live extraction on: {image.name}")
    print(f"  Provider: {provider} / Model: {model}")

    raw = svc.extract_from_image(
        image_path=image,
        provider=provider,
        model_name=model or "claude-opus-4-5",
        api_key=api_key,
        drawing_context={
            "unit_name":      "TEST",
            "drawing_number": "TEST-PID-001",
            "drawing_title":  "Test Extraction",
            "page_number":    1,
        },
    )

    assert raw and len(raw) > 10, "LLM returned an empty or very short response"

    parsed = svc.parse_llm_response(raw)
    assert isinstance(parsed, dict)
    assert "equipment_tags" in parsed
    assert "instrument_tags" in parsed

    total = len(parsed.get("equipment_tags", [])) + len(parsed.get("instrument_tags", []))
    print(f"\n  ✓ Live extraction found {total} tags, confidence={parsed.get('extraction_confidence')}")


# ── Standalone runner ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("parse_llm_response: clean JSON",                 test_parse_clean_json),
        ("parse_llm_response: markdown ```json```",        test_parse_markdown_code_block),
        ("parse_llm_response: markdown ``` no lang",       test_parse_markdown_no_language),
        ("parse_llm_response: with preamble text",         test_parse_response_with_preamble),
        ("parse_llm_response: empty raises ValueError",    test_parse_empty_response_raises),
        ("parse_llm_response: garbage raises ValueError",  test_parse_garbage_raises),
        ("parse_llm_response: truncated raises ValueError",test_parse_partial_json_raises),
        ("parse_llm_response: equipment_tags structure",   test_parse_equipment_tags_structure),
        ("parse_llm_response: instrument_tags structure",  test_parse_instrument_tags_structure),
        ("parse_llm_response: connectivity structure",     test_parse_connectivity_structure),
        ("parse_llm_response: confidence field",           test_parse_confidence_field),
        ("parse_json_array: clean array",                  test_parse_array_clean),
        ("parse_json_array: markdown wrapped",             test_parse_array_markdown_wrapped),
        ("parse_json_array: empty input → []",             test_parse_array_empty_input_returns_empty),
        ("parse_json_array: garbage → []",                 test_parse_array_garbage_returns_empty),
        ("parse_json_array: dict input → []",              test_parse_array_dict_input_returns_empty),
        ("parse_json_array: literal [] → []",              test_parse_array_empty_array),
        ("extract_from_image: missing path raises",        test_extract_missing_image_raises),
        ("extract_from_image: unknown provider raises",    test_extract_unknown_provider_raises),
        ("get_provider_client: invalid raises",            test_get_provider_client_invalid_raises),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except pytest.skip.Exception as exc:
            print(f"  SKIP  {name}")
            print(f"         → {exc}")
        except Exception as exc:
            print(f"  FAIL  {name}")
            print(f"         → {exc}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if failed == 0 else 1)
