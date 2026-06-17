"""
llm_service.py — LLM provider abstraction
Provides a single interface for calling Claude, OpenAI, or Gemini
to extract tags from P&ID drawing images.
"""

import base64
import json
import re
from pathlib import Path


# ── Extraction prompt template ─────────────────────────────────────────────────
# {unit_name}, {drawing_number}, etc. are replaced at call time.
# {{ and }} are escaped braces that become { } in the final prompt string.
# This is the exact prompt the LLM receives — do not change lightly.

def _build_extraction_prompt(drawing_context: dict) -> str:
    """Build the extraction prompt by injecting drawing context into the template."""
    template = """You are an expert P&ID (Piping and Instrumentation Diagram) reader for a petroleum refinery.
Analyze this P&ID drawing image carefully and extract ALL of the following items.

Drawing Context:
- Unit: {unit_name}
- Drawing Number: {drawing_number}
- Drawing Title: {drawing_title}
- Page: {page_number}

Extract and return ONLY a valid JSON object with this exact structure:

{{
  "equipment_tags": [
    {{
      "tag_number": "P-101A",
      "tag_type": "PUMP",
      "description": "Crude Charge Pump",
      "service": "Crude oil transfer",
      "design_pressure": "50 kg/cm2g",
      "design_temp": "150°C",
      "capacity": "200 m3/hr",
      "material": "CS",
      "notes": ""
    }}
  ],
  "instrument_tags": [
    {{
      "tag_number": "FIC-1001",
      "instrument_type": "FIC",
      "description": "Feed Flow Controller",
      "process_variable": "FLOW",
      "service": "Crude feed flow control",
      "range_low": "0",
      "range_high": "500",
      "unit_of_measure": "m3/hr",
      "notes": ""
    }}
  ],
  "line_specs": [
    {{
      "line_number": "6\\"-HN-1001-150#-A1A",
      "nominal_diameter": "6\\"",
      "fluid_service": "HN",
      "line_sequence": "1001",
      "pressure_class": "150#",
      "pipe_spec": "A1A",
      "insulation_code": "",
      "tracing_code": "",
      "from_equipment": "P-101A",
      "to_equipment": "E-201",
      "notes": ""
    }}
  ],
  "drawing_references": [
    {{
      "referenced_drawing": "NRL-CDU-PID-002",
      "reference_type": "CONTINUATION",
      "notes": "Continues on sheet 2"
    }}
  ],
  "connectivity": [
    {{
      "source_tag": "P-101A",
      "source_tag_type": "EQUIPMENT",
      "target_tag": "E-201",
      "target_tag_type": "EQUIPMENT",
      "direction": "DOWNSTREAM",
      "via_line": "6\\"-HN-1001-150#-A1A"
    }}
  ],
  "extraction_confidence": "HIGH",
  "extraction_notes": "Any warnings or observations about image quality or unclear items"
}}

Rules:
1. Extract EVERY visible tag — do not skip any
2. For unclear or partial tags, include them with a note in the notes field
3. For connectivity, trace the flow direction based on arrows and process flow
4. Tag types for equipment: PUMP, COMPRESSOR, VESSEL, DRUM, COLUMN, HEAT_EXCHANGER, FURNACE, COOLER, FILTER, TANK, REACTOR, MIXER, VALVE, OTHERS
5. Instrument types: FIC, FT, TIC, TT, PIC, PT, LIC, LT, FCV, TCV, PCV, LCV, XV, PSV, PRV, FI, TI, PI, LI, OTHERS
6. Return ONLY the JSON. No explanation text before or after."""

    return template.format(**drawing_context)


# ── LLM Service class ─────────────────────────────────────────────────────────

class LLMService:
    """
    Unified interface for calling different LLM providers.
    The caller chooses the provider; this class handles the differences.
    """

    def get_provider_client(self, provider: str, api_key: str):
        """
        Return the API client object for the given provider.
        The client is created fresh each time — not cached, to respect any key changes.
        """
        if provider == "claude":
            import anthropic
            return anthropic.Anthropic(api_key=api_key)

        elif provider == "openai":
            import openai
            return openai.OpenAI(api_key=api_key)

        elif provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            return genai   # return the configured module — models are created per call

        else:
            raise ValueError(
                f"Unknown LLM provider: '{provider}'. "
                f"Supported providers: claude, openai, gemini"
            )

    def extract_from_image(
        self,
        image_path: str | Path,
        provider: str,
        model_name: str,
        api_key: str,
        drawing_context: dict,
    ) -> str:
        """
        Read a P&ID page image, send it to the LLM with the extraction prompt,
        and return the raw text response from the model.

        drawing_context must contain: unit_name, drawing_number, drawing_title, page_number

        Returns the raw LLM text (should be JSON — use parse_llm_response to decode).
        Raises RuntimeError with a clear message if the API call fails.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Page image not found: {image_path}")

        # Read and base64-encode the image (needed for Claude and OpenAI)
        image_bytes = image_path.read_bytes()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Build the text prompt with drawing context filled in
        prompt = _build_extraction_prompt(drawing_context)

        try:
            if provider == "claude":
                return self._extract_claude(image_b64, prompt, model_name, api_key)
            elif provider == "openai":
                return self._extract_openai(image_b64, prompt, model_name, api_key)
            elif provider == "gemini":
                return self._extract_gemini(image_path, prompt, model_name, api_key)
            else:
                raise ValueError(f"Unknown provider: {provider}")
        except (FileNotFoundError, ValueError):
            raise   # re-raise without wrapping
        except Exception as err:
            raise RuntimeError(
                f"LLM API call failed ({provider}/{model_name}): {err}"
            ) from err

    # ── Provider-specific private methods ─────────────────────────────────────

    def _extract_claude(self, image_b64: str, prompt: str, model_name: str, api_key: str) -> str:
        """Call Anthropic Claude with the image encoded as base64."""
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model=model_name,
            max_tokens=8192,   # P&IDs can have many tags — use a generous limit
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return response.content[0].text

    def _extract_openai(self, image_b64: str, prompt: str, model_name: str, api_key: str) -> str:
        """Call OpenAI GPT-4o (or similar vision model) with the image as a data URL."""
        import openai
        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model_name,
            max_tokens=8192,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                                "detail": "high",   # request high-detail image analysis
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return response.choices[0].message.content

    def _extract_gemini(self, image_path: Path, prompt: str, model_name: str, api_key: str) -> str:
        """Call Google Gemini with the image loaded via Pillow."""
        import google.generativeai as genai
        from PIL import Image as PILImage

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        # Gemini accepts a PIL image directly
        pil_image = PILImage.open(str(image_path))
        response = model.generate_content(
            [prompt, pil_image],
            generation_config={"max_output_tokens": 8192},
            request_options={"timeout": 120},   # fail fast if API hangs
        )
        return response.text

    def analyze_image(
        self,
        image_path: str | Path,
        prompt: str,
        provider: str,
        model_name: str,
        api_key: str,
    ) -> str:
        """
        Send an image + a caller-provided prompt to the LLM and return the raw text response.
        Unlike extract_from_image, the prompt is built by the caller — use this for
        document page analysis, not P&ID extraction.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        image_bytes = image_path.read_bytes()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        try:
            if provider == "claude":
                return self._extract_claude(image_b64, prompt, model_name, api_key)
            elif provider == "openai":
                return self._extract_openai(image_b64, prompt, model_name, api_key)
            elif provider == "gemini":
                return self._extract_gemini(image_path, prompt, model_name, api_key)
            else:
                raise ValueError(f"Unknown provider: {provider}")
        except (FileNotFoundError, ValueError):
            raise
        except Exception as err:
            raise RuntimeError(
                f"LLM API call failed ({provider}/{model_name}): {err}"
            ) from err

    # ── Response parsing ───────────────────────────────────────────────────────

    def parse_llm_response(self, raw_response: str) -> dict:
        """
        Parse the LLM's text output as JSON.
        LLMs sometimes wrap the JSON in markdown code blocks — this handles that.
        Raises ValueError with the raw response if nothing can be parsed.
        """
        if not raw_response or not raw_response.strip():
            raise ValueError("LLM returned an empty response.")

        text = raw_response.strip()

        # Attempt 1: direct JSON parse (ideal case — LLM followed instructions)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Attempt 2: extract from ```json ... ``` code block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Attempt 3: find the first { ... } block in the text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # All attempts failed
        preview = text[:300] + ("..." if len(text) > 300 else "")
        raise ValueError(
            f"Could not parse LLM response as JSON.\n"
            f"First 300 chars of raw response:\n{preview}"
        )

    def parse_json_array_response(self, raw_response: str) -> list:
        """
        Parse the LLM's text output as a JSON array (list).
        Used for document tag indexing where the LLM returns [...] not {...}.
        Handles the same markdown code-block wrapping that parse_llm_response handles.
        Returns an empty list if nothing is found.
        """
        if not raw_response or not raw_response.strip():
            return []

        text = raw_response.strip()

        # Attempt 1: direct parse
        try:
            result = json.loads(text)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            pass

        # Attempt 2: extract from ```json ... ``` block
        match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                return result if isinstance(result, list) else []
            except json.JSONDecodeError:
                pass

        # Attempt 3: find the first [ ... ] block
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(0))
                return result if isinstance(result, list) else []
            except json.JSONDecodeError:
                pass

        # Give up gracefully — return empty list so indexing doesn't hard-fail
        return []
