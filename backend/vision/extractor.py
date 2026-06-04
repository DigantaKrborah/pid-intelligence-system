import base64
import json
from pathlib import Path
from typing import Optional
import google.generativeai as genai
from pdf2image import convert_from_path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.config import get_settings

EXTRACTION_PROMPT = """
You are an expert P&ID (Piping & Instrumentation Diagram) analyser for process engineering.

Analyse this P&ID drawing page and extract ALL equipment and instrument tags you can identify.

For each tag found, return:
- tag: the tag identifier (e.g., P-101, TIC-301, V-201, FCV-101)
- tag_type: one of: pump | vessel | valve | instrument | exchanger | compressor | line | heater | cooler | other
- description: brief description of what this equipment is
- connected_to: list of other tags this equipment is directly connected to (max 10)
- line_number: pipe/line number if visible

Return ONLY a JSON object with this structure:
{
  "tags": [
    {
      "tag": "P-101",
      "tag_type": "pump",
      "description": "Feed pump",
      "connected_to": ["V-101", "FCV-101"],
      "line_number": "4\"-CS-001"
    }
  ],
  "sheet_number": "P&ID-CDU-001",
  "process_description": "one sentence describing what process this sheet shows"
}

Be thorough — extract every tag visible. If uncertain about a tag, still include it with lower implied confidence.
"""


class PIDExtractor:
    def __init__(self):
        self.settings = get_settings()
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel(self.settings.gemini_vision_model)

    def pdf_to_images(self, pdf_path: str, dpi: int = 200) -> list[Path]:
        """Convert PDF pages to images, return list of image paths."""
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def extract_from_image(self, image_path: Path) -> dict:
        """Send one P&ID page image to Gemini Vision, return extracted tags."""
        image_data = image_path.read_bytes()
        b64 = base64.b64encode(image_data).decode()

        response = self.model.generate_content(
            [
                {"mime_type": "image/png", "data": b64},
                EXTRACTION_PROMPT,
            ]
        )

        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed for {image_path.name}: {e}")
            result = {"tags": [], "sheet_number": "", "process_description": ""}

        logger.info(f"Extracted {len(result.get('tags', []))} tags from {image_path.name}")
        return result

    def extract_from_pdf(self, pdf_path: str) -> list[dict]:
        """Extract tags from all pages of a PDF. Returns list of per-page results."""
        image_paths = self.pdf_to_images(pdf_path)
        results = []
        for img_path in image_paths:
            try:
                result = self.extract_from_image(img_path)
                result["page_number"] = int(img_path.stem.split("_")[1])
                result["image_path"] = str(img_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to extract from {img_path.name}: {e}")
                results.append({
                    "page_number": int(img_path.stem.split("_")[1]),
                    "tags": [],
                    "error": str(e),
                })
        return results
