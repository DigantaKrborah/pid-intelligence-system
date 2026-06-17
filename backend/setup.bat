@echo off
REM ============================================================
REM  P&ID Intelligence System — Backend Setup Script
REM  Run this from the /backend folder:  setup.bat
REM ============================================================

echo.
echo === Installing Python packages ===
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Check your Python installation.
    pause
    exit /b 1
)

echo.
echo === Creating database and applying schema ===
python app/utils/create_db.py
if %errorlevel% neq 0 (
    echo ERROR: Database setup failed. Check your .env values and PostgreSQL connection.
    pause
    exit /b 1
)

echo.
echo === Inserting seed data ===
python app/utils/seed_db.py
if %errorlevel% neq 0 (
    echo ERROR: Seed data insertion failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup complete! You can now start the backend with:
echo    uvicorn app.main:app --reload --port 8000
echo ============================================================
pause
