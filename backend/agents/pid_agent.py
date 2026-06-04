"""
P&ID Agent — specialist for P&ID document provenance and sheet-level queries.
Tells the coordinator which sheet/page a tag came from.
"""
from loguru import logger


class PIDAgent:
    """Queries PostgreSQL for tag provenance (which sheet/page a tag was extracted from)."""

    def get_tag_provenance(self, tag: str, unit_name: str) -> dict:
        """Return the source P&ID document and page number for a tag."""
        try:
            from sqlalchemy import create_engine, text
            from backend.config import get_settings

            settings = get_settings()
            sync_url = settings.database_url.replace("+asyncpg", "+psycopg2", 1)

            engine = create_engine(sync_url)
            with engine.connect() as conn:
                row = conn.execute(
                    text(
                        "SELECT et.tag, et.tag_type, et.description, et.page_number, "
                        "       pd.original_filename "
                        "FROM equipment_tags et "
                        "LEFT JOIN pid_documents pd ON et.document_id = pd.id "
                        "JOIN units u ON et.unit_id = u.id "
                        "WHERE et.tag = :tag AND u.name = :unit "
                        "LIMIT 1"
                    ),
                    {"tag": tag.upper(), "unit": unit_name.upper()},
                ).fetchone()

            if not row:
                return {"tag": tag, "found": False}

            return {
                "tag": row[0],
                "tag_type": row[1],
                "description": row[2],
                "page_number": row[3],
                "source_document": row[4],
                "found": True,
            }
        except Exception as exc:
            logger.warning(f"PIDAgent.get_tag_provenance failed: {exc}")
            return {"tag": tag, "found": False, "error": str(exc)}

    def list_pid_sheets(self, unit_name: str) -> dict:
        """List all processed P&ID documents for a unit."""
        try:
            from sqlalchemy import create_engine, text
            from backend.config import get_settings

            settings = get_settings()
            sync_url = settings.database_url.replace("+asyncpg", "+psycopg2", 1)

            engine = create_engine(sync_url)
            with engine.connect() as conn:
                rows = conn.execute(
                    text(
                        "SELECT pd.original_filename, pd.page_count, pd.tags_extracted, "
                        "       pd.processing_status "
                        "FROM pid_documents pd "
                        "JOIN units u ON pd.unit_id = u.id "
                        "WHERE u.name = :unit AND pd.processing_status = 'completed' "
                        "ORDER BY pd.uploaded_at DESC"
                    ),
                    {"unit": unit_name.upper()},
                ).fetchall()

            return {
                "unit": unit_name,
                "sheet_count": len(rows),
                "sheets": [
                    {"filename": r[0], "pages": r[1], "tags": r[2]}
                    for r in rows
                ],
            }
        except Exception as exc:
            logger.warning(f"PIDAgent.list_pid_sheets failed: {exc}")
            return {"unit": unit_name, "sheet_count": 0, "sheets": [], "error": str(exc)}
