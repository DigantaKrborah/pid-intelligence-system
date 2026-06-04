from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.config import get_settings
from backend.db.database import init_db
from backend.api.routes import units, upload, search, graph, query


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting P&ID Intelligence API [{settings.app_env}]")
    await init_db()
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

    app.include_router(units.router,  prefix="/api/v1/units",  tags=["Units"])
    app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
    app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
    app.include_router(graph.router,  prefix="/api/v1/graph",  tags=["Graph"])
    app.include_router(query.router,  prefix="/api/v1/query",  tags=["Query"])

    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
