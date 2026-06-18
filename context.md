# Project Context — P&ID Intelligence System

**Last updated:** 2026-06-18  
**Project root:** `E:\PID_Reader`  
**GitHub:** https://github.com/DigantaKrborah/pid-intelligence-system  
**Branch:** `main` (force-pushed; old Streamlit history replaced by new MVP)

---

## What This Is

AI-powered tool for Numaligarh Refinery Ltd. Engineers upload P&ID PDF drawings, the system
extracts equipment tags via an LLM, and results are stored in PostgreSQL and searchable via a
React web UI. Also supports uploading operating manuals/SOPs for document Q&A (indexed into
ChromaDB via a separate documents flow).

---

## Tech Stack (current — everything below is ACTIVE)

| Layer | Technology | How it runs |
|---|---|---|
| Frontend | React 18 + Vite + Tailwind CSS + TanStack Query v5 + React Router v6 | Locally via `npm run dev` (port 5173) |
| API client | Axios — `frontend/src/api/client.js` | — |
| Backend | Python 3.11 + FastAPI + uvicorn | Docker container (port 8000) |
| Database | PostgreSQL 16 | Docker container (host port 5433 → internal 5432) |
| DB access | psycopg2 with `RealDictCursor` — no ORM | — |
| Auth | JWT (python-jose) + bcrypt — token stored in `localStorage` as `pid_token` | — |
| AI / LLM | Configurable: Claude (anthropic), OpenAI (openai), Gemini (google-generativeai) | — |
| PDF splitting | pdf2image + Poppler (at `C:/poppler/Library/bin`) | — |
| Doc indexing | ChromaDB (local) via `llm_service.analyze_image` | — |
| Config | pydantic-settings — reads env vars injected by docker-compose (`env_file: .env`) | — |

**What is NOT used (deleted):** SQLAlchemy, LangChain, Streamlit, ChromaDB agents,
NetworkX, Ollama, Gemini Vision (for P&IDs — replaced by configurable LLM provider).

---

## Folder Structure

```
E:\PID_Reader\
├── start_all.bat          ← launches both servers; auto-detects LAN IP
├── start_backend.bat      ← backend only
├── start_frontend.bat     ← frontend only
├── setup_venv.bat         ← first-time setup (venv, pip, npm, DB seed)
├── .gitignore             ← excludes .env, uploads/, data/**, chroma_db/, .claude/
├── pyproject.toml         ← pytest → backend/tests, coverage → backend/app
│
├── backend\
│   ├── main.py            ← FastAPI app, CORS from env, router registration
│   ├── requirements.txt
│   ├── .env               ← LOCAL ONLY (gitignored) — DB, JWT, CORS, Poppler
│   ├── .env.example       ← template checked into git
│   ├── run.bat            ← start backend only (legacy, prefer start_backend.bat)
│   ├── setup.bat          ← install deps + create DB (legacy, prefer setup_venv.bat)
│   └── app\
│       ├── api\routes\    ← FastAPI route handlers (thin, delegate to services)
│       │   ├── auth.py        POST /api/auth/login, GET /api/auth/me, POST /api/auth/logout
│       │   ├── units.py       CRUD for process units
│       │   ├── drawings.py    upload PDF, list, delete P&ID drawings
│       │   ├── extraction.py  start extraction, poll status, get results
│       │   ├── tags.py        search tags, get tag detail, unit summary
│       │   ├── documents.py   upload manuals/SOPs, index via LLM, delete
│       │   ├── search.py      global full-text search across tags + docs
│       │   ├── settings.py    GET/POST LLM provider config, GET model catalogue
│       │   ├── audit.py       GET audit log with filters (flat list, not paginated object)
│       │   └── users.py       list users, toggle active, add user (admin only)
│       ├── core\
│       │   ├── config.py      pydantic-settings; reads backend/.env
│       │   ├── database.py    psycopg2 connection pool (init_db_pool / close_db_pool)
│       │   └── dependencies.py  get_db(), get_current_user(), require_admin()
│       ├── models\        (Pydantic request/response schemas — currently sparse)
│       ├── services\
│       │   ├── auth_service.py   password hashing (bcrypt), JWT encode/decode
│       │   ├── llm_service.py    LLMService class — extract_from_image, analyze_image,
│       │   │                     parse_llm_response, parse_json_array_response
│       │   └── file_service.py   PDF → PNG pages via pdf2image/Poppler
│       └── utils\
│           ├── create_db.py   runs schema.sql against PostgreSQL
│           └── seed_db.py     inserts admin user + sample process units
│
├── frontend\
│   ├── package.json
│   ├── vite.config.js     ← host:true (LAN), proxy /api → localhost:8000
│   ├── .env               ← VITE_API_URL= (blank; proxy handles dev routing)
│   ├── .env.production    ← VITE_API_URL=http://[SERVER_IP]:8000 (fill in for builds)
│   └── src\
│       ├── api\client.js  ← axios; baseURL from VITE_API_URL||''; JWT interceptor; 401→/login
│       ├── context\AuthContext.jsx   ← user state, login(), logout(), isAdmin
│       ├── components\
│       │   ├── Layout.jsx             sidebar nav, unit selector
│       │   ├── UploadDrawingModal.jsx  PDF upload (50 MB limit)
│       │   ├── UploadDocumentModal.jsx PDF/docx upload
│       │   └── ExtractionModal.jsx    start extraction, poll status
│       └── pages\
│           ├── LoginPage.jsx
│           ├── Dashboard.jsx
│           ├── UnitsPage.jsx
│           ├── DrawingsPage.jsx
│           ├── DrawingDetailPage.jsx
│           ├── TagSearchPage.jsx
│           ├── TagDetailPage.jsx
│           ├── DocumentsPage.jsx      ← IndexDocumentModal (10min timeout), ViewModal, Delete
│           ├── SettingsPage.jsx       ← admin-only; LLM config, user mgmt, process units
│           └── AuditPage.jsx          ← date/action/user filters, CSV export
│
├── db\
│   ├── schema.sql         ← 13 tables: users, process_units, pid_drawings, equipment_tags,
│   │                         instrument_tags, line_specs, drawing_refs, connectivity,
│   │                         documents, document_chunks, llm_settings, audit_log, processing_jobs
│   ├── seed.sql           ← admin user (admin / Admin@123), sample units (CDU, VDU, HCU...)
│   └── migrations\
│
├── uploads\               ← all user-uploaded files (gitignored entirely)
│   ├── pid_drawings\
│   ├── manuals\
│   └── sop\
│
├── data\                  ← runtime data (gitignored except .gitkeep)
│   ├── pids\              ← where file_service.py saves extracted PNG pages
│   ├── manuals\
│   └── graphs\
│
└── docs\
    ├── HOW_TO_RUN.md      ← step-by-step first-run guide
    └── NETWORK_SETUP.md   ← LAN access, firewall, Task Scheduler, pg_dump backups
```

---

## Key Architecture Decisions

### Docker setup
Three services defined in `docker-compose.yml`:
- **postgres** — PostgreSQL 16, data persisted in `postgres_data` volume, health-checked
- **backend** — FastAPI app; `PYTHONPATH=/app:/app/backend` (both needed: `/app` for
  `uvicorn backend.main:app`, `/app/backend` for `from app.*` imports); hot-reload via
  `./backend:/app/backend` volume mount
- **frontend** — Node 20 Alpine running `npm run dev`; port 5173; anonymous volume
  `/app/frontend/node_modules` prevents the host's Windows node_modules from overriding
  the Linux ones in the container

The `DATABASE_URL` in `.env` uses SQLAlchemy async format (`postgresql+asyncpg://`).
`database.py` strips the driver prefix before passing it to psycopg2 via `_psycopg2_dsn()`.

In development, the frontend is typically run locally (`npm run dev` on the host) rather than
via Docker, because port 5173 is usually already bound. The backend and postgres always run
in Docker. The Vite proxy uses `process.env.BACKEND_URL || 'http://localhost:8000'` so it
routes correctly whether running inside Docker (`BACKEND_URL=http://backend:8000`) or locally.

### Database access
Pure psycopg2 with `RealDictCursor`. Every route that needs the DB calls `get_db()` which
returns a connection from the pool. UUIDs must be cast with `::text` in queries because
psycopg2 returns them as `uuid.UUID` objects which don't JSON-serialise automatically.

### Auth flow
1. `POST /api/auth/login` → returns `{ access_token, token_type, user }`
2. Token stored in `localStorage` as `pid_token`
3. Every axios request attaches `Authorization: Bearer <token>` via request interceptor
4. On 401 response: interceptor clears localStorage and redirects to `/login`
5. `get_current_user()` dependency decodes JWT; `require_admin()` checks `role == 'admin'`

### LLM extraction flow
1. User uploads PDF → `file_service.py` splits into per-page PNG files → saved to `data/pids/{drawing_id}/page_NNN.png`
2. User triggers extraction → background task in `extraction.py` iterates pages
3. Each page: `LLMService.extract_from_image()` calls the configured provider (Claude/OpenAI/Gemini)
4. Response parsed with `parse_llm_response()` (handles markdown fences, preamble text)
5. Extracted tags written to `equipment_tags`, `instrument_tags`, `line_specs`, `connectivity` tables
6. `processing_jobs` table tracks status (pending → processing → completed/failed)

### Document indexing flow
1. User uploads PDF/docx → stored in `data/manuals/{document_id}/`
2. `POST /api/documents/{id}/index` → synchronous, blocks until done (10 min axios timeout)
3. Each page analysed via `LLMService.analyze_image()` → chunks written to ChromaDB

### CORS
`backend/.env` has `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`
`main.py` parses this as a comma-separated list and always includes localhost as a safety net.
To add a server IP for LAN access: append `http://192.168.x.x:5173` to CORS_ORIGINS.

### Frontend API routing
- **Dev mode**: `VITE_API_URL` is blank → axios `baseURL=''` → Vite proxy forwards `/api/*` to `localhost:8000`
- **Production build**: set `VITE_API_URL=http://192.168.x.x:8000` in `frontend/.env.production` then `npm run build`

### React Query v5 notes
- `onSuccess` / `onError` callbacks removed from `useQuery` in v5 — use `useEffect` watching `data`
- `keepPreviousData: true` is v4 syntax — use `placeholderData: keepPreviousData` in v5
- All pages use `{ data: foo = [], isLoading, error }` destructuring pattern

### Audit log
`GET /api/audit/` returns a **flat array** (not `{ total, logs: [...] }`).
Frontend AuditPage uses `logs.length === PAGE_LIMIT (50)` to detect hasNext page.
Audit action strings: `LOGIN`, `LOGOUT`, `CREATE_UNIT`, `UPDATE_UNIT`, `UPLOAD_DRAWING`,
`DELETE_DRAWING`, `START_EXTRACTION`, `UPLOAD_DOCUMENT`, `INDEX_DOCUMENT`, `DELETE_DOCUMENT`,
`UPDATE_SETTINGS`, `CREATE_USER`, `TOGGLE_USER`

---

## Environment Files

### `.env` (root — gitignored, used by docker-compose `env_file: .env`)
```
DATABASE_URL=postgresql+asyncpg://pid_user:dev_password@postgres:5432/pid_intelligence
POSTGRES_DB=pid_intelligence
POSTGRES_USER=pid_user
POSTGRES_PASSWORD=dev_password
UPLOAD_BASE_PATH=/app/uploads
JWT_SECRET=[32-char random hex]
JWT_EXPIRE_HOURS=8
DEFAULT_LLM_PROVIDER=claude
POPPLER_PATH=C:/poppler/Library/bin
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```
The `DATABASE_URL` host is `postgres` (Docker service name) — works inside Docker network.
`database.py` converts `postgresql+asyncpg://` → `postgresql://` before psycopg2 sees it.

### `frontend/.env` (gitignored)
```
VITE_API_URL=       ← blank for dev (Vite proxy handles it)
```

### `frontend/.env.production` (gitignored — fill in for builds)
```
VITE_API_URL=http://[SERVER_IP]:8000
```

---

## Running the App

```
# Start backend + postgres (Docker):
docker-compose up -d postgres backend

# Start frontend (locally, in a separate terminal):
cd frontend
npm run dev

# Login:
http://localhost:5173
username: admin
password: Admin@123

# Or start everything in Docker (frontend on port 5173):
docker-compose up -d

# Rebuild after requirements.txt changes:
docker-compose build --no-cache backend
docker-compose up -d backend
```

**Legacy bat files** (`start_all.bat`, `setup_venv.bat`, etc.) still exist for running the
backend outside Docker, but the Docker workflow above is the current standard.

---

## Tests

```
cd backend
python -m pytest tests/test_extraction.py -v    ← 20 unit tests, no live services needed
python -m pytest tests/test_flow.py -v          ← integration tests, requires running backend
```

`test_extraction.py` — tests `LLMService.parse_llm_response` and `parse_json_array_response`
(clean JSON, markdown fences, preamble text, empty/garbage input, error cases). 20 pass, 1 skipped.

`test_flow.py` — full HTTP flow: login, units CRUD, drawings, tag search, settings, audit,
users, extraction status. Requires `uvicorn main:app` running on port 8000.

---

## Known Bugs Fixed (do not reintroduce)

| Bug | Fix location |
|---|---|
| `GET /api/audit/` returned `{ total, logs }` object; frontend expected flat array | `audit.py` → returns `[dict(r) for r in rows]` |
| `api_key: str` (required) in LLMSettingsRequest caused 422 when updating provider without re-entering key | `settings.py` → `api_key: Optional[str] = None`; falls back to existing DB hint |
| Audit action stored as `UPLOAD_PID` but frontend badge map used `UPLOAD_DRAWING` | `drawings.py` → action changed to `'UPLOAD_DRAWING'` |
| `print()` statements in extraction.py and documents.py | Replaced with `logger.info/warning/error()` (loguru) |
| `onSuccess` in SettingsPage useQuery (removed in react-query v5) | Removed; `useEffect` watching `current` data handles population |
| `keepPreviousData: true` in AuditPage (v4 syntax) | Removed |
| `GET /api/audit/` was registered as `GET /logs` causing 404 | `audit.py` → route changed to `GET /` |
| Docker backend: `ModuleNotFoundError: No module named 'app'` | `docker-compose.yml` → `PYTHONPATH: /app:/app/backend` |
| Docker backend: `ModuleNotFoundError: No module named 'jose'` | `requirements.txt` → added `python-jose[cryptography]==3.3.0` |
| Docker backend: `psycopg2.ProgrammingError: invalid dsn` (asyncpg URL passed to psycopg2) | `database.py` → `_psycopg2_dsn()` strips `+asyncpg` driver prefix |
| Docker frontend: Streamlit `app.py` entrypoint no longer exists (frontend is React/Vite) | `Dockerfile.frontend` → rewritten to Node 20; `docker-compose.yml` → port 5173, `npm run dev` |
| File uploads broke when `Content-Type: application/json` was set globally on axios | `client.js` → removed hardcoded `Content-Type` header; axios sets it per-request |

---

## What's NOT Implemented Yet (future prompts)

- Graph/network visualisation of equipment connectivity (NetworkX was planned, not built)
- Chat/Q&A interface for querying extracted tags via natural language
- Document Q&A (ChromaDB indexed but no query endpoint wired to frontend)
- Cross-unit analysis
- Email notifications
- V2 features: RBAC, SSO, cloud storage option
