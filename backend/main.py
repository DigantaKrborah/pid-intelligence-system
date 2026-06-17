"""
main.py — FastAPI application entry point
Start the server from the /backend folder with:   run.bat   (or see run.bat for the uvicorn command)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all route modules
from app.api.routes import auth, units, drawings, extraction, tags, documents
from app.api.routes import search, users
from app.api.routes import settings as settings_router  # renamed to avoid clash with Python built-in
from app.api.routes import audit

# Import database pool helpers
from app.core.database import init_db_pool, close_db_pool

# Import settings so we can read CORS_ORIGINS from the .env file
from app.core.config import get_settings


# ── CORS origins — built from the CORS_ORIGINS environment variable ───────────
# The env variable is a comma-separated list, e.g.:
#   CORS_ORIGINS=http://localhost:5173,http://192.168.1.100:5173
#
# localhost:5173 and 127.0.0.1:5173 are always included so local dev never
# breaks even if someone forgets to set the env variable.
_settings = get_settings()
_origins_from_env = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
_ALWAYS_ALLOWED = ["http://localhost:5173", "http://127.0.0.1:5173"]
ALLOWED_ORIGINS = list(dict.fromkeys(_ALWAYS_ALLOWED + _origins_from_env))  # dedup, order preserved


# ── Create the FastAPI app ─────────────────────────────────────────────────────
app = FastAPI(
    title="P&ID Intelligence System API",
    description="AI-powered P&ID drawing extraction and query system for Numaligarh Refinery Ltd",
    version="1.0.0",
)


# ── CORS — allow the React frontend to call this API ──────────────────────────
# To add your server's network IP, set CORS_ORIGINS in backend/.env:
#   CORS_ORIGINS=http://localhost:5173,http://192.168.1.100:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],     # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],     # Authorization header, Content-Type, etc.
)


# ── Startup / shutdown events ──────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    """Runs once when the server starts — initialises the database pool."""
    print("Starting P&ID Intelligence System API...")
    init_db_pool()


@app.on_event("shutdown")
def on_shutdown():
    """Runs once when the server stops — closes all database connections."""
    close_db_pool()


# ── Register routers ───────────────────────────────────────────────────────────
# Each router handles a group of related API endpoints.
# prefix= sets the URL path prefix for all routes in that file.
app.include_router(auth.router,            prefix="/api/auth",       tags=["Authentication"])
app.include_router(units.router,           prefix="/api/units",      tags=["Process Units"])
app.include_router(drawings.router,        prefix="/api/drawings",   tags=["P&ID Drawings"])
app.include_router(extraction.router,      prefix="/api/extraction", tags=["AI Extraction"])
app.include_router(tags.router,            prefix="/api/tags",       tags=["Equipment Tags"])
app.include_router(documents.router,       prefix="/api/documents",  tags=["Documents"])
app.include_router(search.router,          prefix="/api/search",     tags=["Search"])
app.include_router(settings_router.router, prefix="/api/settings",   tags=["LLM Settings"])
app.include_router(audit.router,           prefix="/api/audit",      tags=["Audit Logs"])
app.include_router(users.router,           prefix="/api/users",      tags=["User Management"])


# ── Health check endpoint ──────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    """Quick health check — open http://localhost:8000 in a browser to verify the server is running."""
    return {"status": "ok", "app": "P&ID Intelligence System"}
