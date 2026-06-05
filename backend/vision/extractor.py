"""
P&ID Vision Extractor — Tesseract OCR backend.

Reads text from image-only P&ID PDFs using Tesseract OCR.
No cloud API or large model required.

Falls back to Gemini Flash if GEMINI_API_KEY starts with 'AIza'.
"""
import re
import json
import base64
import httpx
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.config import get_settings

# ── Tag patterns ──────────────────────────────────────────────────────────────
# Matches: 04-VV-002, 04-P-001A, P-101, TIC-301, E-172B, FCV-101
_TAG_PAT = re.compile(
    r'\b(?:\d{2,4}-[A-Z]{1,5}-\d{2,4}[A-Z]?'   # 04-VV-002 style
    r'|[A-Z]{1,5}-\d{2,4}[A-Z]?)\b'              # P-101 / E-172B style
)

# Equipment type mapping from tag prefix
_TYPE_MAP = {
    "P":   "pump",       "CP":  "pump",       "PP":  "pump",
    "V":   "vessel",     "VV":  "vessel",     "T":   "vessel",
    "TK":  "vessel",     "D":   "vessel",     "DR":  "vessel",
    "E":   "exchanger",  "HE":  "exchanger",  "AE":  "exchanger",
    "C":   "compressor", "K":   "compressor",
    "FCV": "valve",      "LV":  "valve",      "PCV": "valve",
    "HV":  "valve",      "XV":  "valve",      "SDV": "valve",
    "FIC": "instrument", "LIC": "instrument", "PIC": "instrument",
    "TIC": "instrument", "FT":  "instrument", "LT":  "instrument",
    "PT":  "instrument", "TT":  "instrument", "AT":  "instrument",
    "FE":  "instrument", "TE":  "instrument", "PE":  "instrument",
    "H":   "heater",     "F":   "heater",     "B":   "heater",
}

EXTRACTION_PROMPT = """You are an expert P&ID (Piping & Instrumentation Diagram) analyser.

Analyse this P&ID drawing and extract ALL equipment and instrument tags visible.

Tag formats vary by plant:
  Standard ISA:    P-101, TIC-301, V-201, FCV-101, E-101
  Area-type-seq:   04-VV-002, 04-P-001, 04-TIC-001, 12-E-005

For each tag return:
- tag: EXACT tag identifier as printed
- tag_type: pump | vessel | valve | instrument | exchanger | compressor | line | heater | other
- description: brief description
- connected_to: list of directly connected tags (max 10)
- line_number: pipe line number if visible

Return ONLY valid JSON:
{
  "tags": [
    {"tag": "04-VV-002", "tag_type": "vessel", "description": "Filtered feed charge drum",
     "connected_to": ["04-P-001"], "line_number": ""}
  ],
  "sheet_number": "",
  "process_description": ""
}
Extract EVERY tag. Return only the JSON object."""


def _is_valid_gemini_key(key: str) -> bool:
    return key.startswith("AIza") and len(key) > 30


def _guess_type(tag: str) -> str:
    """Guess equipment type from tag prefix."""
    # Handle area-prefix format: 04-VV-002 → prefix = VV
    parts = tag.split("-")
    if len(parts) == 3 and parts[0].isdigit():
        prefix = parts[1].upper()
    else:
        prefix = parts[0].upper()
    return _TYPE_MAP.get(prefix, "other")


class PIDExtractor:
    def __init__(self):
        self.settings = get_settings()
        self._use_gemini = _is_valid_gemini_key(self.settings.gemini_api_key)
        if self._use_gemini:
            logger.info("Vision backend: Gemini Flash")
        else:
            logger.info("Vision backend: Tesseract OCR (local)")

    # ── PDF → images ──────────────────────────────────────────────────────────

    def pdf_to_images(self, pdf_path: str, dpi: int = 200) -> list[Path]:
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
        return self._extract_ocr(image_path)

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
        return self._parse_llm_response(response.text, image_path.name)

    def _extract_ocr(self, image_path: Path) -> dict:
        """
        Extract equipment tags using Tesseract OCR.
        Pre-processes image for better OCR accuracy on P&ID drawings.
        """
        try:
            import pytesseract
            from PIL import Image, ImageFilter, ImageEnhance
            import cv2
            import numpy as np

            # Load and preprocess
            img = Image.open(image_path).convert("L")          # grayscale

            # Upscale if small (helps OCR)
            w, h = img.size
            if min(w, h) < 1500:
                scale = 1500 / min(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

            # Enhance contrast
            img = ImageEnhance.Contrast(img).enhance(2.0)
            img = ImageEnhance.Sharpness(img).enhance(2.0)

            # Threshold for cleaner text
            arr = np.array(img)
            _, arr = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            img = Image.fromarray(arr)

            # Run OCR — use PSM 11 (sparse text) to catch scattered tags
            ocr_text = pytesseract.image_to_string(
                img,
                config="--psm 11 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-/ ",
            )

            logger.debug(f"OCR raw text ({image_path.name}): {ocr_text[:300]}")

            # Extract tags from OCR text
            found_tags = list(set(_TAG_PAT.findall(ocr_text.upper())))
            found_tags = [t for t in found_tags if len(t) >= 4]  # filter noise

            tags = [
                {
                    "tag":          tag,
                    "tag_type":     _guess_type(tag),
                    "description":  "",
                    "connected_to": [],
                    "line_number":  "",
                }
                for tag in sorted(found_tags)
            ]

            logger.info(f"OCR extracted {len(tags)} tags from {image_path.name}")
            return {
                "tags":                found_tags and tags or [],
                "sheet_number":        "",
                "process_description": f"Extracted via OCR from {image_path.name}",
            }

        except Exception as e:
            logger.error(f"OCR failed for {image_path.name}: {e}")
            return {"tags": [], "sheet_number": "", "process_description": ""}

    def _parse_llm_response(self, raw: str, filename: str) -> dict:
        raw = raw.strip()
        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip().lstrip("json").strip()
                if part.startswith("{"):
                    raw = part
                    break
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        try:
            result = json.loads(raw)
            logger.info(f"LLM extracted {len(result.get('tags', []))} tags from {filename}")
            return result
        except Exception as e:
            logger.warning(f"JSON parse failed for {filename}: {e}")
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
