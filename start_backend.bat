@echo off
REM ============================================================
REM  P&ID Intelligence System — Start Backend Only
REM  Run from the project root:  start_backend.bat
REM  Useful for backend-only development.
REM ============================================================

echo.
echo   Starting FastAPI backend on port 8000...
echo   API docs:  http://localhost:8000/docs
echo.
cd /d %~dp0backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
