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

# Equipment type mapping from tag prefix — only KNOWN equipment prefixes
_TYPE_MAP = {
    # Pumps
    "P": "pump",  "CP": "pump",  "PP": "pump",  "GP": "pump",
    # Vessels / drums / columns
    "V": "vessel",  "VV": "vessel",  "T": "vessel",  "TK": "vessel",
    "D": "vessel",  "DR": "vessel",  "KO": "vessel",  "FA": "vessel",
    # Exchangers / coolers
    "E": "exchanger",  "HE": "exchanger",  "AE": "exchanger",
    "EA": "exchanger",  "EE": "exchanger",  "AC": "exchanger",
    # Compressors / turbines
    "C": "compressor",  "K": "compressor",  "KA": "compressor",
    "PT": "compressor",  "GT": "compressor",
    # Valves
    "FCV": "valve",  "LV": "valve",  "PCV": "valve",  "PV": "valve",
    "HV": "valve",   "XV": "valve",  "SDV": "valve",  "TV": "valve",
    "FV": "valve",   "BV": "valve",  "MOV": "valve",  "PSV": "valve",
    "PRV": "valve",  "CV": "valve",  "TCV": "valve",  "LCV": "valve",
    # Instruments / transmitters / indicators
    "FIC": "instrument",  "LIC": "instrument",  "PIC": "instrument",
    "TIC": "instrument",  "FT":  "instrument",  "LT":  "instrument",
    "PT":  "instrument",  "TT":  "instrument",  "AT":  "instrument",
    "FE":  "instrument",  "TE":  "instrument",  "PE":  "instrument",
    "FI":  "instrument",  "LI":  "instrument",  "PI":  "instrument",
    "TI":  "instrument",  "AI":  "instrument",  "FQ":  "instrument",
    "FS":  "instrument",  "LS":  "instrument",  "PS":  "instrument",
    "TS":  "instrument",  "FC":  "instrument",  "LC":  "instrument",
    "PC":  "instrument",  "TC":  "instrument",  "FR":  "instrument",
    # Heaters / furnaces
    "H": "heater",  "F": "heater",  "B": "heater",  "HF": "heater",
    # Filters / strainers
    "FL": "other",  "STR": "other",
    # Mixers / agitators
    "MX": "other",  "AG": "other",
    # Lines
    "L": "line",
}

# Noise prefixes to reject — drawing labels, notes, utility codes
_NOISE_PREFIXES = {
    "NOTE", "WCR", "WCS", "WDM", "WDN", "WOR", "WP", "SL",
    "OS", "PHE", "BTL", "GPL", "QAKFL", "CEWCR", "TOKA", "TOW",
    "CBD", "BEP", "ASP", "RF", "DE", "CC", "M", "RI", "GN",
    "SP", "RE", "VS", "RS", "PB", "RT",
}


def _is_valid_equipment_tag(tag: str) -> bool:
    """Return True only if the tag looks like a real equipment tag, not a drawing annotation."""
    parts = tag.split("-")

    # Area-format: 04-VV-002 — middle part must be a known type
    if len(parts) == 3 and parts[0].isdigit():
        prefix = parts[1].upper()
        return prefix in _TYPE_MAP

    # Standard format: P-101, FCV-001, E-172B
    if len(parts) >= 2:
        prefix = parts[0].upper()
        if prefix in _NOISE_PREFIXES:
            return False
        # Accept if it's a known type OR looks like an equipment tag (2-3 letters + numbers)
        if prefix in _TYPE_MAP:
            return True
        # Reject if prefix is a single digit or all-lowercase
        if len(prefix) <= 1 or not prefix[0].isalpha():
            return False
        # Reject long noise prefixes (5+ chars) not in type map
        if len(prefix) > 4:
            return False
        # Accept short unknown prefixes (could be plant-specific)
        return True

    return False

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

            # Run OCR — PSM 6 (single block) captures more descriptive text
            # alongside PSM 11 (sparse) for scattered tags
            ocr_sparse = pytesseract.image_to_string(
                img,
                config="--psm 11 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-/ ",
            )
            # Second pass without whitelist to capture full description text
            ocr_full = pytesseract.image_to_string(img, config="--psm 6 --oem 3")

            combined_text = ocr_sparse + "\n" + ocr_full
            logger.debug(f"OCR raw ({image_path.name}): {combined_text[:400]}")

            # Extract tags from OCR text — apply equipment tag filter
            raw_tags   = list(set(_TAG_PAT.findall(combined_text.upper())))
            found_tags = [t for t in raw_tags if len(t) >= 4 and _is_valid_equipment_tag(t)]
            logger.debug(f"OCR raw={len(raw_tags)}, after filter={len(found_tags)}: {found_tags}")

            if not found_tags:
                return {"tags": [], "sheet_number": "", "process_description": ""}

            # ── Step 2: use qwen3:8b to extract descriptions + connections from OCR text ──
            enriched_tags = self._enrich_with_llm(found_tags, combined_text, image_path.name)

            logger.info(f"OCR+LLM extracted {len(enriched_tags)} tags from {image_path.name}")
            return {
                "tags":                enriched_tags,
                "sheet_number":        "",
                "process_description": f"Extracted via OCR+LLM from {image_path.name}",
            }

        except Exception as e:
            logger.error(f"OCR failed for {image_path.name}: {e}")
            return {"tags": [], "sheet_number": "", "process_description": ""}

    def _enrich_with_llm(self, found_tags: list[str], ocr_text: str, filename: str) -> list[dict]:
        """
        Send OCR-extracted tags + raw OCR text to qwen3:8b.
        The LLM reads the text context to assign descriptions and infer connections.
        Falls back to basic tag objects if LLM call fails.
        """
        tag_list = ", ".join(found_tags)
        prompt = f"""You are a P&ID engineering expert. Below is raw text extracted by OCR from a P&ID drawing page.

Equipment tags found: {tag_list}

OCR text from the drawing:
{ocr_text[:3000]}

For EACH tag listed above, provide:
1. description: the equipment name/function from the text (e.g. "Fractionator overhead accumulator", "Make-up hydrogen compressor first intercooler")
2. tag_type: pump | vessel | valve | instrument | exchanger | compressor | heater | other
3. connected_to: list of other tags that are likely connected based on the context (max 5)

Use the OCR text as context. If a description is not clear, make a reasonable inference from the tag name and nearby text.

Return ONLY valid JSON (no explanation, no markdown):
{{
  "tags": [
    {{"tag": "04-VV-010", "tag_type": "vessel", "description": "Fractionator overhead accumulator", "connected_to": ["04-EA-002A", "04-PA-012A"], "line_number": ""}},
    {{"tag": "04-EA-002A", "tag_type": "exchanger", "description": "Fractionator overhead air cooler train A", "connected_to": ["04-VV-010"], "line_number": ""}}
  ]
}}"""

        try:
            resp = httpx.post(
                f"{self.settings.ollama_base_url}/api/generate",
                json={
                    "model":   self.settings.ollama_chat_model,
                    "prompt":  prompt,
                    "stream":  False,
                    "options": {"temperature": 0, "num_predict": 2048},
                },
                timeout=90,
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "")

            # Strip <think> tokens from qwen3
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

            # Parse JSON
            start, end = raw.find("{"), raw.rfind("}") + 1
            if start != -1 and end > start:
                result = json.loads(raw[start:end])
                enriched = result.get("tags", [])
                if enriched:
                    # Ensure all found tags are present (LLM might drop some)
                    llm_tags = {t["tag"] for t in enriched}
                    for tag in found_tags:
                        if tag not in llm_tags:
                            enriched.append({
                                "tag": tag, "tag_type": _guess_type(tag),
                                "description": "", "connected_to": [], "line_number": "",
                            })
                    logger.info(f"LLM enriched {len(enriched)} tags for {filename}")
                    return enriched

        except Exception as e:
            logger.warning(f"LLM enrichment failed for {filename}: {e} — using basic tags")

        # Fallback: return basic tag objects without descriptions
        return [
            {"tag": t, "tag_type": _guess_type(t), "description": "", "connected_to": [], "line_number": ""}
            for t in sorted(found_tags)
        ]

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
