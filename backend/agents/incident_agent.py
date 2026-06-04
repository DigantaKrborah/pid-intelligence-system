"""
Incident Agent — specialist for correlating process incidents with equipment tags.
Queries PostgreSQL incidents table for tag-correlated incidents.
"""
from loguru import logger


class IncidentAgent:
    """
    Queries incidents from the database.
    Uses a sync DB session since it's called from within a sync LangChain tool.
    """

    def find_related_incidents(self, tag: str, unit_name: str) -> dict:
        """
        Find open or recent incidents whose related_tags list contains the given tag.
        Returns a summary suitable for agent reasoning.
        """
        try:
            from sqlalchemy import create_engine, text
            from backend.config import get_settings

            settings = get_settings()
            # Convert async URL to sync for blocking call inside tool
            sync_url = settings.database_url.replace("+asyncpg", "+psycopg2", 1)

            engine = create_engine(sync_url)
            with engine.connect() as conn:
                rows = conn.execute(
                    text(
                        "SELECT title, severity, status, description, related_tags "
                        "FROM incidents "
                        "WHERE related_tags @> :tag_arr "
                        "ORDER BY reported_at DESC LIMIT 5"
                    ),
                    {"tag_arr": f'["{tag}"]'},
                ).fetchall()

            incidents = [
                {
                    "title": r[0],
                    "severity": r[1],
                    "status": r[2],
                    "description": (r[3] or "")[:200],
                }
                for r in rows
            ]
            return {
                "tag": tag,
                "unit": unit_name,
                "incidents_found": len(incidents),
                "incidents": incidents,
            }
        except Exception as exc:
            logger.warning(f"IncidentAgent.find_related_incidents failed: {exc}")
            return {"tag": tag, "unit": unit_name, "incidents_found": 0, "incidents": [], "error": str(exc)}

    def get_open_incidents(self, unit_name: str) -> dict:
        """Return all open incidents for a unit."""
        try:
            from sqlalchemy import create_engine, text
            from backend.config import get_settings

            settings = get_settings()
            sync_url = settings.database_url.replace("+asyncpg", "+psycopg2", 1)

            engine = create_engine(sync_url)
            with engine.connect() as conn:
                rows = conn.execute(
                    text(
                        "SELECT title, severity, status, related_tags "
                        "FROM incidents "
                        "WHERE status != 'resolved' "
                        "ORDER BY reported_at DESC LIMIT 10"
                    )
                ).fetchall()

            return {
                "unit": unit_name,
                "open_incidents": len(rows),
                "incidents": [
                    {"title": r[0], "severity": r[1], "status": r[2]}
                    for r in rows
                ],
            }
        except Exception as exc:
            logger.warning(f"IncidentAgent.get_open_incidents failed: {exc}")
            return {"unit": unit_name, "open_incidents": 0, "incidents": [], "error": str(exc)}
