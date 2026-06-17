@echo off
REM ============================================================
REM  P&ID Intelligence System — Start Frontend Only
REM  Run from the project root:  start_frontend.bat
REM  Requires the backend to already be running on port 8000.
REM ============================================================

echo.
echo   Starting React frontend on port 5173...
echo   Open in browser:  http://localhost:5173
echo.
echo   (The backend must be running separately on port 8000)
echo   (Use start_backend.bat or start_all.bat to launch both)
echo.
cd /d %~dp0frontend
npm run dev
