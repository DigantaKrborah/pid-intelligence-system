"""
PDF Processing Pipeline (M1)

Flow: PDF file → page images → Gemini Vision → tags → PostgreSQL + NetworkX + ChromaDB
"""
import asyncio
import uuid
from pathlib import Path
from loguru import logger

from backend.config import get_settings
from backend.db.database import get_session_factory
from backend.db.repositories.document_repo import DocumentRepository
from backend.db.repositories.unit_repo import UnitRepository
from backend.graph.builder import GraphBuilder

_graph_builder = GraphBuilder()


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

                # Persist each tag
                tag_objects: dict[str, uuid.UUID] = {}
                for tag_data in tags:
                    tag_str = tag_data.get("tag", "").strip()
                    if not tag_str:
                        continue

                    tag_obj = await doc_repo.upsert_tag(
                        unit_id=unit_id,
                        document_id=document_id,
                        tag=tag_str,
                        tag_type=tag_data.get("tag_type"),
                        description=tag_data.get("description"),
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
                        "description": tag_data.get("description", ""),
                    })

                    # Add node to NetworkX graph
                    _graph_builder.add_equipment(
                        unit_name=unit.name,
                        tag=tag_str,
                        tag_type=tag_data.get("tag_type", "other"),
                        description=tag_data.get("description", ""),
                        document_id=str(document_id),
                        page_number=page_num,
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
                        _graph_builder.add_connection(
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
            _graph_builder.save(unit.name)
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
