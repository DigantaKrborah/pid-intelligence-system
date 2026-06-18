# Project Status — P&ID Intelligence System

**Last updated:** 2026-06-18  
**Current phase:** MVP complete — all pages built, bugs fixed, Docker setup repaired and running

---

## Summary

| Stage | Description | Status |
|---|---|---|
| 1 | Project scaffold | ✅ Complete |
| 2 | Database (schema + seed) | ✅ Complete |
| 3 | Backend (FastAPI routes + services) | ✅ Complete |
| 4 | Frontend (React pages + components) | ✅ Complete |
| 5 | Integration testing + bug fixes | ✅ Complete |
| 6A | Network / multi-user support | ✅ Complete |
| 6B | Docker setup repair | ✅ Complete |
| 6C+ | Scale-up (future) | ⏳ Not started |

---

## Stage 1 — Project Scaffold

| Prompt | Description | Status |
|---|---|---|
| 1A | Folder structure, .gitignore, .env.example | ✅ Done |

---

## Stage 2 — Database

| Prompt | Description | Status |
|---|---|---|
| 2A | `db/schema.sql` — 13 tables, auto-update triggers | ✅ Done |
| 2B | `create_db.py`, `requirements.txt`, `setup.bat`, `backend/.env` | ✅ Done |
| 2C | `db/seed.sql` + `seed_db.py` (admin user + sample units) | ✅ Done |

**Admin credentials (from seed.sql):** `admin` / `Admin@123`  
**Sample units seeded:** CDU, VDU, HCU (and others)

---

## Stage 3 — Backend (FastAPI)

| Prompt | Description | Status |
|---|---|---|
| 3A | `config.py`, `database.py`, `main.py`, `run.bat`, 9 route stubs | ✅ Done |
| 3B | `auth_service.py`, `dependencies.py`, `auth.py` (login/me/logout + audit) | ✅ Done |
| 3C | `file_service.py`, `units.py` (3 endpoints), `drawings.py` (4 endpoints) | ✅ Done |
| 3D | `llm_service.py` (Claude/OpenAI/Gemini), `extraction.py` (4 endpoints + bg task) | ✅ Done |
| 3E | `tags.py` (search, detail, unit summary), `search.py` (global search) | ✅ Done |
| 3F | `documents.py` (upload, index via LLM, view, delete) | ✅ Done |
| 3G | `settings.py` (LLM config GET/POST + model catalogue), `audit.py` | ✅ Done |
| 3H | `users.py` (list, toggle active, add user — admin only) | ✅ Done |

**All routes live at:** `backend/app/api/routes/`  
**All routes registered in:** `backend/main.py`

---

## Stage 4 — Frontend (React)

| Prompt | Description | Status |
|---|---|---|
| 4A | Vite config, routing, `AuthContext`, `Layout`, `LoginPage` | ✅ Done |
| 4B | `Dashboard`, `UnitsPage` | ✅ Done |
| 4C | `DrawingsPage`, `UploadDrawingModal`, `ExtractionModal`, `DrawingDetailPage` | ✅ Done |
| 4D | `TagSearchPage`, `TagDetailPage` | ✅ Done |
| 4E | `DocumentsPage`, `UploadDocumentModal`, `SettingsPage`, `AuditPage` | ✅ Done |

---

## Stage 5 — Integration Testing & Bug Fixes

| Step | Description | Status |
|---|---|---|
| 5A-1 | Audit all backend routes for import/null/CORS issues | ✅ Done |
| 5A-2 | Audit all frontend files for token attachment, loading states | ✅ Done |
| 5A-3 | `backend/tests/test_flow.py` — 20-step HTTP integration test | ✅ Done |
| 5A-4 | `backend/tests/test_extraction.py` — 20 unit tests (20 pass, 1 skipped) | ✅ Done |
| 5A-5 | Fix all bugs found | ✅ Done |

**Bugs fixed:**
1. `audit.py` — route `/logs` → `/`; response changed to flat array
2. `settings.py` — `api_key` made Optional with DB fallback
3. `drawings.py` — audit action `UPLOAD_PID` → `UPLOAD_DRAWING`
4. `extraction.py` — 10× `print()` → `logger.info/warning/error()`
5. `documents.py` — 2× `print()` → `logger.error/warning()`
6. `SettingsPage.jsx` — removed `onSuccess` (invalid in react-query v5)
7. `AuditPage.jsx` — removed `keepPreviousData: true` (v4 syntax)

---

## Stage 6 — Scale-Up

| Prompt | Description | Status |
|---|---|---|
| 6A | Multi-user / LAN network access | ✅ Done |
| 6B | Docker setup repair | ✅ Done |
| 6C+ | (future) | ⏳ Not started |

**6A changes:**
- `main.py` — CORS origins read from `CORS_ORIGINS` env var (comma-separated)
- `config.py` — added `cors_origins` field
- `vite.config.js` — `host: true` (0.0.0.0) + `/api` proxy to localhost:8000
- `client.js` — `baseURL: import.meta.env.VITE_API_URL || ''`
- `frontend/.env.production` — template with `VITE_API_URL=http://[SERVER_IP]:8000`
- `start_all.bat` — auto-detects LAN IP via PowerShell, prints network URLs
- `docs/NETWORK_SETUP.md` — firewall, Task Scheduler, pg_dump backup guide

**6B changes (2026-06-18):**
- `docker-compose.yml` — `PYTHONPATH: /app:/app/backend` (was `/app` only; `from app.*`
  imports failed because `/app/backend` was not on the path)
- `requirements.txt` — added `python-jose[cryptography]==3.3.0` and `bcrypt==4.2.1`
  (root file is what Docker builds from; `backend/requirements.txt` is legacy/local only)
- `backend/app/core/database.py` — added `_psycopg2_dsn()` to strip `postgresql+asyncpg://`
  prefix before passing `DATABASE_URL` to psycopg2 (which requires plain `postgresql://`)
- `docker/Dockerfile.frontend` — rewritten from Python/Streamlit to Node 20 Alpine; old
  `frontend/app.py` Streamlit entrypoint no longer exists (frontend is React/Vite)
- `docker-compose.yml` frontend service — port `8501→5173`, command `npm run dev`, added
  anonymous volume for `/app/frontend/node_modules`
- `frontend/vite.config.js` — Vite proxy target uses `process.env.BACKEND_URL ||
  'http://localhost:8000'` so Docker container routes to the `backend` service correctly
- `frontend/src/api/client.js` — removed hardcoded `Content-Type: application/json` header
  (broke multipart/form-data file uploads; axios sets the correct header automatically)
- `db/schema.sql` + `docker/init.sql` — added `api_key TEXT` column to `llm_settings` table;
  `extraction.py` reads the full key from DB for the "use saved settings" flow
- `db/seed.sql` — fixed bcrypt hash for `Admin@123` (old hash didn't verify correctly)
- `backend/app/api/routes/extraction.py` — background task now applies `_psycopg2_dsn()`
  before `psycopg2.connect()` (same asyncpg prefix bug as `database.py`)
- `backend/app/core/config.py` — `poppler_path: Optional[str] = None`; no longer hardcoded
- `.env` (root) — `POPPLER_PATH=` (empty) so docker-compose injects it as env var, which
  pydantic-settings picks up with higher priority than the `backend/.env` file value
  (`C:/poppler-25.12.0/Library/bin`); `file_service.py` converts empty string → `None` so
  pdf2image uses system PATH where `pdftoppm` lives (`/usr/bin/pdftoppm` in the container)

---

## Folder Cleanup

| Action | Description | Status |
|---|---|---|
| Created | `start_all.bat`, `start_backend.bat`, `start_frontend.bat`, `setup_venv.bat` | ✅ Done |
| Created | `docs/HOW_TO_RUN.md` | ✅ Done |
| Deleted | All Streamlit frontend code (`frontend/app.py`, `frontend/pages/`, `frontend/utils/`, `frontend/.streamlit/`) | ✅ Done |
| Deleted | All old backend architecture (`backend/agents/`, `backend/api/` top-level, `backend/config.py`, `backend/db/`, `backend/graph/`, `backend/rag/`, `backend/services/`, `backend/models/`, `backend/vision/`) | ✅ Done |
| Deleted | Root-level `tests/` (old Streamlit-era tests; active tests now in `backend/tests/`) | ✅ Done |
| Updated | `.gitignore` — fixed data/** patterns; added `.claude/` | ✅ Done |
| Updated | `pyproject.toml` — `testpaths = ["backend/tests"]` | ✅ Done |

---

## Git

| Action | Status |
|---|---|
| First commit `afd87c2` on `main` — 107 files, 17,571 insertions | ✅ Done |
| Pushed `feature/react-mvp` branch (intermediate step) | ✅ Deleted |
| Force-pushed to `main` on GitHub (replaced Streamlit history) | ✅ Done |

**Remote:** https://github.com/DigantaKrborah/pid-intelligence-system  
**Branch:** `main`  
**HEAD:** `afd87c2` feat(all): initial commit — P&ID Intelligence System MVP

---

## What Works Right Now

- Full auth flow (login, JWT, role-based access, audit trail)
- Process unit CRUD
- P&ID PDF upload → split to pages → LLM extraction → tag storage
- Equipment tag search and detail view
- Document upload + LLM page indexing
- Settings page (LLM provider/model/key, user management, unit editing)
- Audit log with filters and CSV export
- LAN network access (with correct .env config)

## What Is NOT Built Yet

- **Graph visualisation** — connectivity data is extracted and stored in DB, but no graph UI
- **Chat / Q&A** — ChromaDB indexing works, but no natural language query endpoint/UI
- **Cross-unit analysis** endpoint
- **Email notifications**
- **V2:** RBAC, SSO, cloud storage, mobile-responsive improvements
