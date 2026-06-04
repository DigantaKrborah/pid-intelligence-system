from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.config import get_settings
from backend.db.database import init_db, get_session_factory
from backend.services.graph_service import ensure_all_graphs_loaded
from backend.api.routes import units, upload, search, graph, query, incidents


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting P&ID Intelligence API [{settings.app_env}]")
    await init_db()
    factory = get_session_factory()
    async with factory() as session:
        await ensure_all_graphs_loaded(session)
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="P&ID Intelligence System",
        description="AI-powered P&ID knowledge graph and NL query engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(units.router,     prefix="/api/v1/units",     tags=["Units"])
    app.include_router(upload.router,    prefix="/api/v1/upload",    tags=["Upload"])
    app.include_router(search.router,    prefix="/api/v1/search",    tags=["Search"])
    app.include_router(graph.router,     prefix="/api/v1/graph",     tags=["Graph"])
    app.include_router(query.router,     prefix="/api/v1/query",     tags=["Query"])
    app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["Incidents"])

    @app.get("/health")
    async def health():
        """Liveness check — verifies DB and Ollama reachability."""
        import httpx
        from sqlalchemy import text
        from backend.db.database import get_engine

        checks: dict[str, str] = {"api": "ok", "env": settings.app_env}

        # PostgreSQL check
        try:
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"

        # Ollama check
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                r = await client.get(f"{settings.ollama_base_url}/api/tags")
            checks["ollama"] = "ok" if r.status_code == 200 else f"http {r.status_code}"
        except Exception:
            checks["ollama"] = "unreachable"

        overall = "ok" if all(v in ("ok", settings.app_env) for v in checks.values()) else "degraded"
        return {"status": overall, **checks}

    return app


app = create_app()
