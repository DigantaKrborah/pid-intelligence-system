@echo off
REM ============================================================
REM  P&ID Intelligence System — First-Time Setup
REM  Run this ONCE before starting the app for the first time.
REM  Run from the project root:  setup_venv.bat
REM ============================================================

echo.
echo ============================================================
echo   P&ID Intelligence System — First-Time Setup
echo ============================================================
echo.


REM ── Step 1: Check Python is installed ─────────────────────────────────────

python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not on PATH.
    echo Download Python 3.11 from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo   Python found: %PY_VER%


REM ── Step 2: Create virtual environment ────────────────────────────────────
REM  The .venv folder is created in the project root.
REM  This keeps Python packages isolated from other projects.

if exist .venv (
    echo   Virtual environment already exists — skipping creation.
) else (
    echo.
    echo   Creating Python virtual environment in .venv\ ...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo   Done.
)


REM ── Step 3: Install Python packages ───────────────────────────────────────

echo.
echo   Installing Python packages from backend\requirements.txt ...
.venv\Scripts\pip install --upgrade pip -q
.venv\Scripts\pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Check backend\requirements.txt.
    pause
    exit /b 1
)
echo   Done.


REM ── Step 4: Check Node.js is installed ────────────────────────────────────

node --version > nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Node.js is not installed. Frontend will not run.
    echo Download Node.js from https://nodejs.org  (LTS version recommended)
    echo Skipping frontend install.
    goto :setup_env
)

for /f %%v in ('node --version') do set NODE_VER=%%v
echo   Node.js found: %NODE_VER%


REM ── Step 5: Install frontend npm packages ─────────────────────────────────

echo.
echo   Installing frontend packages from frontend\package.json ...
cd /d %~dp0frontend
npm install
if %errorlevel% neq 0 (
    echo ERROR: npm install failed. Check frontend\package.json.
    cd /d %~dp0
    pause
    exit /b 1
)
cd /d %~dp0
echo   Done.


REM ── Step 6: Create .env from template (if not already present) ────────────

:setup_env
echo.
if exist backend\.env (
    echo   backend\.env already exists — skipping copy.
) else (
    copy backend\.env.example backend\.env > nul
    echo   Created backend\.env from template.
    echo.
    echo   IMPORTANT: Edit backend\.env now and fill in:
    echo     DATABASE_URL  — your PostgreSQL connection string
    echo     JWT_SECRET    — a random 32-char string (run: python -c "import secrets; print(secrets.token_hex(32))")
)


REM ── Step 7: Set up the database ───────────────────────────────────────────

echo.
echo   Setting up database schema and seed data...
.venv\Scripts\python backend\app\utils\create_db.py
if %errorlevel% neq 0 (
    echo WARNING: Database setup failed.
    echo Make sure PostgreSQL is running and DATABASE_URL in backend\.env is correct.
    echo Run 'python backend\app\utils\create_db.py' manually after fixing .env.
) else (
    .venv\Scripts\python backend\app\utils\seed_db.py
    if %errorlevel% neq 0 (
        echo WARNING: Seed data failed — schema may already be seeded.
    )
    echo   Database ready.
)


REM ── Done ──────────────────────────────────────────────────────────────────

echo.
echo ============================================================
echo   Setup complete!
echo.
echo   Next steps:
echo     1. Edit backend\.env  (fill in DATABASE_URL and JWT_SECRET)
echo     2. Run start_all.bat  to launch the application
echo     3. Open http://localhost:5173 in your browser
echo     4. Log in with:  admin / Admin@123
echo ============================================================
echo.
pause
