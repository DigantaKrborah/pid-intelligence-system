"""
file_service.py — File storage helpers
Used by the drawings upload route to save files and convert PDFs to images.
All files stay on local disk — nothing is sent to the cloud.
"""

import shutil
from pathlib import Path
from typing import Optional

# Only these file types are accepted for P&ID drawings
ALLOWED_FILE_TYPES = {"pdf", "jpg", "jpeg", "png", "tiff"}


def get_file_type(filename: str) -> str:
    """
    Return the lowercase file extension without the dot.
    Example: "drawing.PDF" → "pdf"
    """
    return Path(filename).suffix.lstrip(".").lower()


def validate_file_type(filename: str) -> bool:
    """Return True if the file extension is in the allowed list."""
    return get_file_type(filename) in ALLOWED_FILE_TYPES


def sanitize_folder_name(name: str) -> str:
    """
    Make a string safe to use as a folder name on Windows.
    Replaces characters that are not allowed in Windows paths.
    Example: "NRL/CDU-001" → "NRL_CDU-001"
    """
    unsafe_chars = r'/\:*?"<>|'
    result = name
    for ch in unsafe_chars:
        result = result.replace(ch, "_")
    return result.strip()


def save_upload_file(content: bytes, destination_path: Path) -> Path:
    """
    Write raw file bytes to destination_path.
    Creates any missing parent folders automatically.
    Returns the path where the file was saved.
    """
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_bytes(content)
    return destination_path


def convert_pdf_to_images(
    pdf_path: Path,
    output_folder: Path,
    poppler_path: Optional[str] = None,
) -> list[Path]:
    """
    Convert every page of a PDF to a PNG image using pdf2image (which requires Poppler).
    Images are saved as page_001.png, page_002.png, etc. inside output_folder.
    Returns a list of Path objects pointing to the saved PNG files.

    If Poppler is not installed or pdf2image fails, raises an exception with a helpful message.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise RuntimeError("pdf2image is not installed. Run: pip install pdf2image")

    output_folder.mkdir(parents=True, exist_ok=True)

    try:
        # dpi=150 gives a good balance of quality vs. file size for P&ID sheets
        images = convert_from_path(
            str(pdf_path),
            poppler_path=poppler_path or None,
            dpi=150,
            fmt="png",
        )
    except Exception as err:
        raise RuntimeError(
            f"PDF conversion failed: {err}\n"
            f"Make sure Poppler is installed and POPPLER_PATH in .env is correct."
        )

    saved_paths: list[Path] = []
    for page_num, img in enumerate(images, start=1):
        img_path = output_folder / f"page_{page_num:03d}.png"
        img.save(str(img_path), "PNG")
        saved_paths.append(img_path)

    return saved_paths


def copy_image_as_page(source_path: Path, output_folder: Path) -> Path:
    """
    For single-image uploads (JPG, PNG, TIFF), copy the image to the
    drawings folder as page_001.png so all drawings have a consistent structure.
    Returns the path to page_001.png.
    """
    from PIL import Image

    output_folder.mkdir(parents=True, exist_ok=True)
    page_path = output_folder / "page_001.png"

    # Convert to PNG regardless of input format (handles TIFF, JPEG, etc.)
    img = Image.open(source_path)
    img.save(str(page_path), "PNG")
    return page_path


def delete_drawing_folder(folder_path: Path) -> None:
    """
    Delete the folder that holds a drawing's files.
    Does nothing if the folder does not exist.
    """
    if folder_path.exists() and folder_path.is_dir():
        shutil.rmtree(folder_path)
