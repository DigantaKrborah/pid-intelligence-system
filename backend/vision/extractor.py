"""
P&ID Vision Extractor.

Uses Ollama multimodal (llama4:scout) by default — fully local, no API key.
Falls back to Gemini Flash if GEMINI_API_KEY starts with 'AIza'.
"""
import base64
import json
import httpx
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.config import get_settings

EXTRACTION_PROMPT = """You are an expert P&ID (Piping & Instrumentation Diagram) analyser.

Analyse this P&ID drawing and extract ALL equipment and instrument tags visible.

For each tag return:
- tag: identifier like P-101, TIC-301, V-201, FCV-101, E-101, C-101
- tag_type: pump | vessel | valve | instrument | exchanger | compressor | line | heater | other
- description: brief description
- connected_to: list of directly connected tags (max 10)
- line_number: pipe line number if visible

Return ONLY valid JSON:
{
  "tags": [
    {"tag": "P-101", "tag_type": "pump", "description": "Feed pump", "connected_to": ["V-101"], "line_number": ""}
  ],
  "sheet_number": "",
  "process_description": ""
}

Extract every tag you can see. Return only the JSON object, no other text."""


def _is_valid_gemini_key(key: str) -> bool:
    return key.startswith("AIza") and len(key) > 30


class PIDExtractor:
    def __init__(self):
        self.settings = get_settings()
        self._use_gemini = _is_valid_gemini_key(self.settings.gemini_api_key)
        if self._use_gemini:
            logger.info("Vision backend: Gemini Flash")
        else:
            logger.info("Vision backend: Ollama llama4:scout (local)")

    # ── PDF → images ──────────────────────────────────────────────────────────

    def pdf_to_images(self, pdf_path: str, dpi: int = 150) -> list[Path]:
        from pdf2image import convert_from_path
        pdf_path = Path(pdf_path)
        output_dir = pdf_path.parent / f"{pdf_path.stem}_pages"
        output_dir.mkdir(exist_ok=True)

        pages = convert_from_path(str(pdf_path), dpi=dpi, fmt="png")
        paths = []
        for i, page in enumerate(pages):
            img_path = output_dir / f"page_{i + 1:03d}.png"
            page.save(str(img_path))
            paths.append(img_path)

        logger.info(f"Converted {len(paths)} pages from {pdf_path.name}")
        return paths

    # ── Per-image extraction ───────────────────────────────────────────────────

    def extract_from_image(self, image_path: Path) -> dict:
        if self._use_gemini:
            return self._extract_gemini(image_path)
        return self._extract_ollama(image_path)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=10))
    def _extract_gemini(self, image_path: Path) -> dict:
        import google.generativeai as genai
        genai.configure(api_key=self.settings.gemini_api_key)
        model = genai.GenerativeModel(self.settings.gemini_vision_model)

        b64 = base64.b64encode(image_path.read_bytes()).decode()
        response = model.generate_content([
            {"mime_type": "image/png", "data": b64},
            EXTRACTION_PROMPT,
        ])
        return self._parse_response(response.text, image_path.name)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=8))
    def _extract_ollama(self, image_path: Path) -> dict:
        """Call Ollama multimodal API (llama4:scout supports image input)."""
        b64 = base64.b64encode(image_path.read_bytes()).decode()

        payload = {
            "model":  "llama4:scout",
            "prompt": EXTRACTION_PROMPT,
            "images": [b64],
            "stream": False,
            "options": {"temperature": 0, "num_predict": 2048},
        }

        try:
            resp = httpx.post(
                f"{self.settings.ollama_base_url}/api/generate",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "")
            return self._parse_response(raw, image_path.name)
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama vision error {e.response.status_code}: {e.response.text[:200]}")
            raise

    # ── Parse raw LLM text → structured dict ──────────────────────────────────

    def _parse_response(self, raw: str, filename: str) -> dict:
        raw = raw.strip()
        # Strip markdown fences
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw = part
                    break

        # Find the first { ... } block
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]

        try:
            result = json.loads(raw)
            count = len(result.get("tags", []))
            logger.info(f"Extracted {count} tags from {filename}")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed for {filename}: {e} — raw: {raw[:200]}")
            return {"tags": [], "sheet_number": "", "process_description": ""}

    # ── Full PDF pipeline ──────────────────────────────────────────────────────

    def extract_from_pdf(self, pdf_path: str) -> list[dict]:
        image_paths = self.pdf_to_images(pdf_path)
        results = []
        for img_path in image_paths:
            try:
                result = self.extract_from_image(img_path)
                result["page_number"] = int(img_path.stem.split("_")[1])
                result["image_path"]  = str(img_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to extract from {img_path.name}: {e}")
                results.append({
                    "page_number": int(img_path.stem.split("_")[1]),
                    "tags": [], "error": str(e),
                })
        return results
