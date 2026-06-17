# Project Context

## Key Decisions & Notes

- **Project root**: `E:\PID_Reader` (maps to the `C:\pid-system` path described in prompts)
- **UPLOAD_BASE_PATH** in `.env.example` set to `E:/PID_Reader/uploads` (adjusted from prompt default)
- **Old Streamlit codebase** still exists under `backend/` (agents, rag, vision, etc.) — this is
  the previous architecture and will be superseded by the new React + FastAPI build
- New backend code lives under `backend/app/` to avoid conflict with the old structure
- `frontend/src/` is the new React frontend; old `frontend/app.py` (Streamlit) remains untouched

## Architecture (this session)

- Frontend: React 18 + Vite + Tailwind CSS + React Router + Axios
- Backend:  FastAPI inside `backend/app/`
- DB:       PostgreSQL 15 installed locally on Windows (not Docker)
- Auth:     JWT (to be implemented in a later prompt)
- AI:       Configurable — Claude / OpenAI / Gemini (key entered in Settings UI)

## Prompt History

| Date       | Prompt | Outcome |
|------------|--------|---------|
| 2026-06-17 | 1A     | Folder structure created at E:\PID_Reader |
| 2026-06-17 | 2A     | db/schema.sql written — 13 tables, auto-update triggers |
| 2026-06-17 | 2B     | create_db.py, requirements.txt, setup.bat, backend/.env created |
| 2026-06-17 | 2C     | db/seed.sql + backend/app/utils/seed_db.py created; setup.bat updated |
| 2026-06-17 | 3A     | config.py, database.py, main.py, run.bat, 9 route stubs, 4 __init__.py |
| 2026-06-17 | 3B     | auth_service.py, dependencies.py, auth.py (login/me/logout + audit log) |
| 2026-06-17 | 3C     | file_service.py, units.py (3 endpoints), drawings.py (4 endpoints) |
| 2026-06-17 | 3D     | llm_service.py (3 providers), extraction.py (4 endpoints + bg task) |
