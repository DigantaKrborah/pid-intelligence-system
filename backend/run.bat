@echo off
REM ============================================================
REM  P&ID Intelligence System — Start Backend Server
REM  Run this from the /backend folder:  run.bat
REM  Server starts at: http://localhost:8000
REM  API docs at:      http://localhost:8000/docs
REM ============================================================

echo Starting P&ID Intelligence System backend...
uvicorn main:app --reload --host 0.0.0.0 --port 8000
