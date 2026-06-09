"""
PDF Processing Pipeline (M1)

Flow: PDF file → page images → Tesseract OCR → tags → PostgreSQL + NetworkX + ChromaDB
"""
import asyncio
import re
import uuid
from pathlib import Path
from loguru import logger

from backend.config import get_settings
from backend.db.database import get_session_factory
from backend.db.repositories.document_repo import DocumentRepository
from backend.db.repositories.unit_repo import UnitRepository
from backend.services.graph_service import get_graph_builder as _get_graph_builder

# ── Description helpers ────────────────────────────────────────────────────────

def _sheet_context_from_filename(filename: str) -> str:
    """
    Extract a human-readable context string from the PDF filename.
    e.g. '46. E-195B R3 (Fractionator Ovhd.) DQUP-Model.pdf'
         → 'Fractionator Overhead (E-195B R3)'
    e.g. '26.E-172B R1 (Filtered Feed Charge Drum)-Model.pdf'
         → 'Filtered Feed Charge Drum (E-172B R1)'
    """
    name = Path(filename).stem
    # Extract parenthesised description if present
    paren = re.search(r'\(([^)]+)\)', name)
    # Extract equipment number (E-xxx, KA-xxx pattern)
    equip = re.search(r'\b([A-Z]+-\d+[A-Z]*)\b', name)
    if paren:
        desc = paren.group(1).rstrip(".").strip()
        ref  = equip.group(1) if equip else ""
        return f"{desc} ({ref})" if ref else desc
    # Fall back: clean up the filename
    clean = re.sub(r'\d+\.?\s*', '', name)  # strip leading numbers
    clean = re.sub(r'[-_](model|dqup|r\d).*', '', clean, flags=re.I)
    clean = clean.replace("-", " ").strip().title()
    return clean[:80]


def _is_clean_description(desc: str) -> bool:
    """Return True if the description looks like real equipment text, not OCR noise."""
    if not desc or len(desc) < 8:
        return False
    # Reject if too long — likely picked up the whole right-side legend column
    if len(desc) > 80:
        return False
    # Reject if description looks like another tag name (e.g. "Atlv001B", "04-EE-035B")
    if re.match(r'^[\dA-Z]{2,}-[\dA-Z]', desc, re.I):
        return False
    # Reject known noise patterns
    noise_patterns = [
        r'^\d',                                    # starts with digit
        r'^[A-Z]\s*\d',                            # single letter + digit (A1, B3…)
        r'\b[A-Z]\b.*\b[A-Z]\b.*\b[A-Z]\b',       # 3+ isolated single-letter words
        r'Uy|Hprt|Bsbs|Bia|Ies|Esp|Nol\b|Tus\b|Oro\b|Nnec\b|Seciind|Atlv|Toka',
        r'Seal\s+\d|P\s+04\s+\d',
        r'\bKo\b|\bRm\b|\bTn\b',                  # common OCR letter-pair noise
        r'Train [A-Z]\s+\w+\s+Stage',              # repeated "Train X … Stage" pattern
    ]
    for p in noise_patterns:
        if re.search(p, desc, re.I):
            return False
    # Require at least 2 meaningful words (len > 2 avoids abbreviation noise)
    words = [w for w in desc.split() if len(w) > 2]
    if len(words) < 2:
        return False
    # Accept if it contains a known engineering keyword
    engineering_kw = {
        'accumulator','drum','separator','exchanger','cooler','compressor',
        'pump','vessel','column','reactor','heater','fractionator','overhead',
        'hhps','intercooler','suction','hydrogen','filtered','charge','quench',
        'absorber','stripper','reboiler','condenser','turbine','flash','feed',
        'reflux','bottoms','product','service','utility','cooling','water',
        'nitrogen','steam','hydrogen','sulfide','amine','crude','naphtha',
        'gas','oil','liquid','vapor','mixed','stage','makeup',
    }
    desc_lower = desc.lower()
    return any(kw in desc_lower for kw in engineering_kw)



async def process_pid_document(document_id: uuid.UUID, unit_id: uuid.UUID) -> None:
    """
    Background task: extract tags from all pages of a P&ID PDF and persist them.
    Creates its own DB session since the request session is closed by this point.
    """
    factory = get_session_factory()
    async with factory() as session:
        doc_repo = DocumentRepository(session)
        unit_repo = UnitRepository(session)

        # Fetch records
        doc = await doc_repo.get_document(document_id)
        unit = await unit_repo.get_by_id(unit_id)
        if not doc or not unit:
            logger.error(f"process_pid_document: doc {document_id} or unit {unit_id} not found")
            return

        # Create processing job
        job = await doc_repo.create_processing_job(document_id, "pid")
        job_id = job.id
        await session.commit()

        try:
            # Mark as processing
            await doc_repo.update_status(document_id, "processing")
            await doc_repo.update_job(job_id, "processing")
            await session.commit()

            logger.info(f"Starting extraction for {doc.filename} (unit: {unit.name})")

            # Run sync PID extraction in thread pool
            from backend.vision.extractor import PIDExtractor
            extractor = PIDExtractor()
            page_results = await asyncio.to_thread(extractor.extract_from_pdf, doc.file_path)

            total_tags = 0
            all_tags_for_embedding: list[dict] = []

            for page_result in page_results:
                page_num = page_result.get("page_number", 0)
                tags = page_result.get("tags", [])

                if page_result.get("error"):
                    logger.warning(f"Page {page_num} extraction error: {page_result['error']}")
                    continue

                # Derive a fallback description from the PDF filename if OCR gave nothing
                sheet_context = _sheet_context_from_filename(doc.filename)
                # Human-readable drawing reference shown in graph/chat
                sheet_number = page_result.get("sheet_number", "")
                drawing_ref  = sheet_number or Path(doc.original_filename or doc.filename).stem[:60]

                # Persist each tag
                tag_objects: dict[str, uuid.UUID] = {}
                for tag_data in tags:
                    tag_str = tag_data.get("tag", "").strip()
                    if not tag_str:
                        continue

                    # Use OCR description if clean; fall back to sheet context
                    ocr_desc = (tag_data.get("description") or "").strip()
                    description = ocr_desc if _is_clean_description(ocr_desc) else sheet_context

                    tag_obj = await doc_repo.upsert_tag(
                        unit_id=unit_id,
                        document_id=document_id,
                        tag=tag_str,
                        tag_type=tag_data.get("tag_type"),
                        description=description,
                        page_number=page_num,
                        raw_attributes={
                            "line_number": tag_data.get("line_number"),
                            "connected_to": tag_data.get("connected_to", []),
                        },
                    )
                    tag_objects[tag_str] = tag_obj.id
                    total_tags += 1
                    all_tags_for_embedding.append({
                        "tag": tag_str,
                        "tag_type": tag_data.get("tag_type", ""),
                        "description": description,
                    })

                    # Add node to NetworkX graph
                    _get_graph_builder().add_equipment(
                        unit_name=unit.name,
                        tag=tag_str,
                        tag_type=tag_data.get("tag_type", "other"),
                        description=description,
                        document_id=str(document_id),
                        page_number=page_num,
                        drawing_ref=drawing_ref,
                    )

                # Add edges for connected_to relationships
                for tag_data in tags:
                    source = tag_data.get("tag", "").strip()
                    if not source:
                        continue
                    for target in tag_data.get("connected_to", []):
                        target = target.strip()
                        if not target:
                            continue
                        # Add edge to graph
                        _get_graph_builder().add_connection(
                            unit_name=unit.name,
                            source=source,
                            target=target,
                            connection_type="pipeline",
                        )
                        # Persist connection if both tags exist in DB
                        if source in tag_objects and target in tag_objects:
                            await doc_repo.create_connection(
                                source_id=tag_objects[source],
                                target_id=tag_objects[target],
                            )

            await session.commit()

            # Save NetworkX graph to disk
            _get_graph_builder().save(unit.name)
            logger.info(f"Graph saved for unit {unit.name}")

            # Index tags in ChromaDB for semantic search
            if all_tags_for_embedding:
                await _index_in_chromadb(unit.name, all_tags_for_embedding)

            # Finalise
            await doc_repo.update_status(
                document_id,
                "completed",
                page_count=len(page_results),
                tags_extracted=total_tags,
            )
            await doc_repo.update_job(
                job_id,
                "completed",
                result_summary={"pages": len(page_results), "tags": total_tags},
            )
            await doc_repo.audit("pid.processed", "pid_document", document_id, {"tags": total_tags})
            await session.commit()

            logger.success(f"Completed {doc.filename}: {total_tags} tags from {len(page_results)} pages")

        except Exception as exc:
            logger.exception(f"Processing failed for document {document_id}: {exc}")
            try:
                await doc_repo.update_status(document_id, "failed", error=str(exc))
                await doc_repo.update_job(job_id, "failed", error=str(exc))
                await session.commit()
            except Exception:
                pass


async def _index_in_chromadb(unit_name: str, tags: list[dict]) -> None:
    """Index extracted tags into ChromaDB for semantic search."""
    try:
        from backend.rag.engine import RAGEngine
        rag = RAGEngine()
        await asyncio.to_thread(rag.index_equipment, unit_name, tags)
        logger.info(f"ChromaDB indexed {len(tags)} tags for unit {unit_name}")
    except Exception as exc:
        # ChromaDB indexing failure is non-fatal — graph and SQL are the source of truth
        logger.warning(f"ChromaDB indexing failed (non-fatal): {exc}")
