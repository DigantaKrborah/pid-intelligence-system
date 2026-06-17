@echo off
REM ==========================================================================
REM  P&ID Intelligence System — Start All Services
REM  Double-click this file from the project root to launch everything.
REM
REM  What this script does:
REM    1. Detects the server's local network IP address automatically
REM    2. Starts the FastAPI backend  (port 8000)  in a separate window
REM    3. Starts the React frontend   (port 5173)  in a separate window
REM    4. Shows the URLs your team should use to access the system
REM ==========================================================================

echo.
echo ============================================================
echo   P&ID Intelligence System — Starting up
echo   Numaligarh Refinery Ltd
echo ============================================================
echo.


REM ── Step 1: Detect this machine's LAN IP address ──────────────────────────
REM
REM  We write a tiny PowerShell script to a temp file, run it, and read the
REM  output. This is the most reliable way to find the right IP on Windows
REM  when the machine has multiple network adapters (Wi-Fi, Ethernet, VPN).
REM
REM  The script looks for the network adapter that has a default gateway
REM  (i.e., the one actually connected to your LAN/router).

echo   Detecting local IP address...

REM Write the PowerShell script to a temporary file
echo $adapter = Get-CimInstance Win32_NetworkAdapterConfiguration ^| Where-Object { $_.IPEnabled -and $_.DefaultIPGateway } ^| Select-Object -First 1 > "%TEMP%\pid_getip.ps1"
echo if ($adapter) { $adapter.IPAddress[0] } else { '127.0.0.1' } >> "%TEMP%\pid_getip.ps1"

REM Run the script and capture its output into SERVER_IP
set SERVER_IP=
for /f "usebackq" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\pid_getip.ps1"`) do set SERVER_IP=%%i

REM Clean up temp file
del "%TEMP%\pid_getip.ps1" > nul 2>&1

REM Fall back to localhost if detection failed
if "%SERVER_IP%"=="" set SERVER_IP=localhost


REM ── Step 2: Print the access URLs ─────────────────────────────────────────

echo.
echo ============================================================
echo.
echo   From THIS computer:
echo     App:  http://localhost:5173
echo     API:  http://localhost:8000
echo.
echo   From OTHER computers on the network:
echo     App:  http://%SERVER_IP%:5173
echo     API:  http://%SERVER_IP%:8000/docs
echo.
echo ============================================================
echo.
echo   CHECKLIST before sharing the network URL:
echo.
echo   [ ] Windows Firewall allows TCP ports 5173 and 8000
echo       (see docs\NETWORK_SETUP.md for firewall commands)
echo.
echo   [ ] backend\.env has CORS_ORIGINS including:
echo         http://%SERVER_IP%:5173
echo.
echo   [ ] frontend\.env.production has:
echo         VITE_API_URL=http://%SERVER_IP%:8000
echo       (only needed after running:  npm run build)
echo.
echo   See docs\NETWORK_SETUP.md for full setup instructions.
echo ============================================================
echo.


REM ── Step 3: Start the backend (FastAPI) ───────────────────────────────────
REM
REM  --host 0.0.0.0  tells uvicorn to accept connections from any IP address,
REM                  not just localhost.
REM  --reload        auto-restarts the server when you edit Python files.
REM  --port 8000     the port the API listens on.

echo   Starting backend  (FastAPI  — port 8000) ...
start "P&ID Backend — port 8000" cmd /k "cd /d %~dp0backend && echo Backend starting at http://%SERVER_IP%:8000 && uvicorn main:app --reload --host 0.0.0.0 --port 8000"


REM ── Step 4: Wait 3 seconds for the backend to be ready ────────────────────
REM  The frontend dev server tries to connect to the backend at startup.
REM  A small delay avoids misleading "connection refused" errors in the logs.

timeout /t 3 /nobreak > nul


REM ── Step 5: Start the frontend (React / Vite) ─────────────────────────────
REM
REM  --host  tells Vite to listen on 0.0.0.0 so other computers can open it.
REM          (Same as setting host:true in vite.config.js — both work.)

echo   Starting frontend (React / Vite — port 5173) ...
start "P&ID Frontend — port 5173" cmd /k "cd /d %~dp0frontend && echo Frontend starting at http://%SERVER_IP%:5173 && npm run dev -- --host"


REM ── Step 6: Done ──────────────────────────────────────────────────────────

echo.
echo   Both servers are starting in their own windows.
echo   This launcher window can be closed safely.
echo.
echo   To STOP the servers: close the two server windows
echo   (titled "P&ID Backend" and "P&ID Frontend").
echo.
pause
