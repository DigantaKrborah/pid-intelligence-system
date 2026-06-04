"""
SOP / Manual Processing Pipeline (M3)

Flow: PDF/DOCX file → text extraction → chunking → ChromaDB embedding + indexing
"""
import asyncio
import uuid
from pathlib import Path
from loguru import logger

from backend.db.database import get_session_factory
from backend.db.repositories.sop_repo import SOPRepository
from backend.db.repositories.document_repo import DocumentRepository

# Chunking constants
CHUNK_CHARS = 2000       # ≈ 512 tokens at ~4 chars/token
OVERLAP_CHARS = 200      # ≈ 50 tokens overlap


def extract_text_from_pdf(file_path: str) -> tuple[str, int]:
    """Extract full text from a PDF. Returns (text, page_count)."""
    from pypdf import PdfReader
    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text.strip())
    return "\n\n".join(pages), len(reader.pages)


def extract_text_from_docx(file_path: str) -> tuple[str, int]:
    """Extract full text from a DOCX. Returns (text, estimated_page_count)."""
    from docx import Document
    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs)
    # Rough page estimate: 3000 chars per page
    estimated_pages = max(1, len(text) // 3000)
    return text, estimated_pages


def extract_text(file_path: str) -> tuple[str, int]:
    """Dispatch to the right extractor based on file extension."""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix == ".docx":
        return extract_text_from_docx(file_path)
    raise ValueError(f"Unsupported file type: {suffix}")


def chunk_text(text: str, source: str, chunk_size: int = CHUNK_CHARS, overlap: int = OVERLAP_CHARS) -> list[dict]:
    """
    Split text into overlapping chunks, preferring paragraph boundaries.
    Returns list of {id, content, source, page (estimated)}.
    """
    # First split on paragraph boundaries
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[dict] = []
    current = ""
    chunk_index = 0

    for para in paragraphs:
        # If adding this paragraph exceeds chunk size, flush current
        if current and len(current) + len(para) + 2 > chunk_size:
            chunks.append({
                "id": f"{source}_chunk_{chunk_index:04d}",
                "content": current.strip(),
                "source": source,
                "page": _estimate_page(chunk_index, len(chunks), len(text)),
            })
            chunk_index += 1
            # Keep overlap: last `overlap` chars of current as context
            current = current[-overlap:] + "\n\n" + para if overlap else para
        else:
            current = (current + "\n\n" + para).strip() if current else para

    # Flush remaining text
    if current.strip():
        chunks.append({
            "id": f"{source}_chunk_{chunk_index:04d}",
            "content": current.strip(),
            "source": source,
            "page": _estimate_page(chunk_index, len(chunks), len(text)),
        })

    return chunks


def _estimate_page(chunk_index: int, total_chunks: int, total_chars: int) -> int:
    """Rough page estimate based on chunk position."""
    chars_per_page = 3000
    total_pages = max(1, total_chars // chars_per_page)
    if total_chunks == 0:
        return 1
    return max(1, round(chunk_index / max(total_chunks, 1) * total_pages) + 1)


async def process_sop_document(sop_doc_id: uuid.UUID, unit_name: str) -> None:
    """
    Background task: extract text from SOP/manual, chunk, embed, and index in ChromaDB.
    Creates its own DB session.
    """
    factory = get_session_factory()
    async with factory() as session:
        sop_repo = SOPRepository(session)
        doc = await sop_repo.get(sop_doc_id)
        if not doc:
            logger.error(f"process_sop_document: doc {sop_doc_id} not found")
            return

        logger.info(f"Starting SOP indexing: {doc.filename} for unit {unit_name}")

        try:
            # Extract text in thread (sync I/O)
            text, page_count = await asyncio.to_thread(extract_text, doc.file_path)

            if not text.strip():
                logger.warning(f"No text extracted from {doc.filename}")
                await sop_repo.mark_indexed(sop_doc_id, chunk_count=0, page_count=page_count)
                await session.commit()
                return

            # Chunk text
            chunks = chunk_text(text, source=doc.filename)
            logger.info(f"Created {len(chunks)} chunks from {doc.filename}")

            # Embed and index in ChromaDB (sync, run in thread)
            from backend.rag.engine import RAGEngine
            rag = RAGEngine()
            await asyncio.to_thread(rag.index_document_chunks, unit_name, chunks)

            # Update DB record
            await sop_repo.mark_indexed(sop_doc_id, chunk_count=len(chunks), page_count=page_count)
            await session.commit()

            logger.success(f"SOP indexed: {doc.filename} → {len(chunks)} chunks in ChromaDB")

        except Exception as exc:
            logger.exception(f"SOP processing failed for {sop_doc_id}: {exc}")
            # Mark as failed via metadata (no status column on engineering_documents)
            try:
                await sop_repo.mark_indexed(sop_doc_id, chunk_count=0)
                await session.commit()
            except Exception:
                pass
