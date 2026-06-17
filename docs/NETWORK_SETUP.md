# Network Setup Guide — P&ID Intelligence System

**Audience:** IT administrator or engineer responsible for running this system  
**OS:** Windows 11 (server machine)  
**Goal:** Make the system accessible to multiple users on your local network

---

## Overview

The system runs as two processes on one Windows machine:

| Process | Port | What it does |
|---|---|---|
| FastAPI backend | **8000** | Python API — handles all data, AI, database queries |
| React frontend | **5173** | Web interface — served by the Vite dev server |

Once both are running, anyone on the same network can open `http://[SERVER_IP]:5173` in their browser.

---

## Step 1 — Find the Server's IP Address

On the machine that will run the system, open Command Prompt and run:

```cmd
ipconfig
```

Look for the section matching your network connection. It will show something like:

```
Ethernet adapter Ethernet:
   IPv4 Address. . . . . . . . . . . : 192.168.1.100
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1
```

The **IPv4 Address** (e.g. `192.168.1.100`) is what you need. Write it down — you will use it in the steps below.

> **Tip:** Assign a static IP to this machine in your router's DHCP settings so the IP never changes. Ask your IT team if unsure.

---

## Step 2 — Configure the Backend (CORS)

The backend must explicitly allow the frontend's URL. Edit `backend\.env`:

```env
# Replace 192.168.1.100 with your actual server IP
CORS_ORIGINS=http://localhost:5173,http://192.168.1.100:5173
```

If users access from multiple subnets, add all origins separated by commas:

```env
CORS_ORIGINS=http://localhost:5173,http://192.168.1.100:5173,http://10.0.0.50:5173
```

Save the file, then **restart the backend** for the change to take effect.

---

## Step 3 — Configure the Frontend (Production Build)

> **Note:** For development/MVP use, skip this step. The `start_all.bat` launcher uses
> Vite's built-in dev proxy, so the frontend automatically talks to the correct backend.
> This step is only needed if you run `npm run build` and serve the static files.

Edit `frontend\.env.production`:

```env
VITE_API_URL=http://192.168.1.100:8000
```

Then rebuild the frontend:

```cmd
cd frontend
npm run build
```

The built files go into `frontend\dist\`. Serve that folder with any static file server
(e.g. Nginx, IIS, or `npx serve dist`).

---

## Step 4 — Open Windows Firewall Ports

By default, Windows Firewall blocks incoming connections to custom ports.
Run these commands in an **Administrator** Command Prompt:

```cmd
REM Allow the React frontend
netsh advfirewall firewall add rule name="PID Frontend (5173)" protocol=TCP dir=in localport=5173 action=allow

REM Allow the FastAPI backend
netsh advfirewall firewall add rule name="PID Backend (8000)" protocol=TCP dir=in localport=8000 action=allow
```

To verify the rules were added:

```cmd
netsh advfirewall firewall show rule name="PID Frontend (5173)"
netsh advfirewall firewall show rule name="PID Backend (8000)"
```

To remove the rules later (if needed):

```cmd
netsh advfirewall firewall delete rule name="PID Frontend (5173)"
netsh advfirewall firewall delete rule name="PID Backend (8000)"
```

---

## Step 5 — Start the System

Double-click `start_all.bat` from the project root folder.

The launcher will:
1. Auto-detect the server IP
2. Open the backend in one Command Prompt window
3. Open the frontend in another Command Prompt window
4. Print the URLs to share with your team

Share this URL with all users:

```
http://192.168.1.100:5173
```

---

## Step 6 — Auto-Start on Windows Startup (Task Scheduler)

To make the system start automatically when the server boots:

1. Press `Win + R`, type `taskschd.msc`, press Enter
2. Click **Create Basic Task** in the right panel
3. Fill in:
   - **Name:** `PID Intelligence System`
   - **Trigger:** When the computer starts
   - **Action:** Start a program
   - **Program/script:** `C:\pid-system\start_all.bat`  
     *(adjust path to where you placed the project)*
4. Check **Run whether user is logged on or not**
5. Check **Run with highest privileges**
6. Click Finish, then enter your Windows password when prompted

> **Important:** The startup task runs the batch file non-interactively.
> If PostgreSQL is on the same machine, add a 15-second delay to the task
> (under **Triggers → Edit → Delay task for:** 15 seconds) so the database
> has time to start before the backend connects.

---

## Step 7 — Daily Database Backup

PostgreSQL databases should be backed up regularly. Add a scheduled task that runs `pg_dump` every day.

### Manual backup command

Run in Command Prompt (adjust values to match your `.env`):

```cmd
set PGPASSWORD=dev_password
pg_dump -h localhost -p 5432 -U pid_user -d pid_intelligence -F c -f "C:\pid-backups\pid_%date:~-4,4%%date:~-7,2%%date:~-10,2%.dump"
```

The `-F c` flag creates a compressed binary dump (smaller than plain SQL).

### Automated daily backup via Task Scheduler

1. Create a file `C:\pid-system\backup_db.bat`:

```batch
@echo off
REM Daily PostgreSQL backup for P&ID Intelligence System
REM Place in C:\pid-system\ and schedule with Task Scheduler

REM ── Configuration ──────────────────────────────────────────────────────────
set PGPASSWORD=dev_password
set PG_USER=pid_user
set PG_DB=pid_intelligence
set PG_HOST=localhost
set PG_PORT=5432
set BACKUP_DIR=C:\pid-backups

REM ── Create backup directory if it doesn't exist ────────────────────────────
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM ── Build a filename with today's date (YYYYMMDD) ─────────────────────────
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do (
    set DAY=%%a
    set MONTH=%%b
    set YEAR=%%c
)
set BACKUP_FILE=%BACKUP_DIR%\pid_%YEAR%%MONTH%%DAY%.dump

REM ── Run pg_dump ────────────────────────────────────────────────────────────
echo Backing up database to %BACKUP_FILE% ...
pg_dump -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %PG_DB% -F c -f "%BACKUP_FILE%"

if %errorlevel% equ 0 (
    echo Backup successful: %BACKUP_FILE%
) else (
    echo ERROR: Backup failed! Check PostgreSQL connection.
)

REM ── Delete backups older than 30 days ─────────────────────────────────────
forfiles /p "%BACKUP_DIR%" /s /m *.dump /d -30 /c "cmd /c del @path" > nul 2>&1
```

2. Schedule it in Task Scheduler:
   - **Trigger:** Daily at 02:00 AM (when the system is idle)
   - **Action:** Start a program → `C:\pid-system\backup_db.bat`
   - **Run whether user is logged on or not** ✓

### Restore from a backup

```cmd
set PGPASSWORD=dev_password
pg_restore -h localhost -p 5432 -U pid_user -d pid_intelligence -F c "C:\pid-backups\pid_20260617.dump"
```

---

## Quick Reference

| Task | Command / Location |
|---|---|
| Find server IP | `ipconfig` in Command Prompt |
| Start system | Double-click `start_all.bat` |
| Add server IP to CORS | Edit `backend\.env` → `CORS_ORIGINS=` |
| Add server IP to frontend build | Edit `frontend\.env.production` → `VITE_API_URL=` |
| Open firewall port 5173 | `netsh advfirewall firewall add rule name="PID Frontend (5173)" protocol=TCP dir=in localport=5173 action=allow` |
| Open firewall port 8000 | `netsh advfirewall firewall add rule name="PID Backend (8000)" protocol=TCP dir=in localport=8000 action=allow` |
| Manual DB backup | `pg_dump -h localhost -U pid_user -d pid_intelligence -F c -f backup.dump` |
| Restore DB backup | `pg_restore -h localhost -U pid_user -d pid_intelligence -F c backup.dump` |

---

## Troubleshooting

**"This site can't be reached" from another computer**  
→ Firewall ports not open. Run the `netsh` commands in Step 4.

**Login works but data doesn't load (blank tables)**  
→ CORS is blocking API calls. Add the server IP to `CORS_ORIGINS` in `backend\.env` and restart the backend.

**Frontend loads but API calls fail in production build**  
→ `VITE_API_URL` in `frontend\.env.production` is wrong or still has the `[SERVER_IP]` placeholder. Set it to the real IP and rebuild.

**IP address changed after router restart**  
→ Assign a static IP to the server in your router's DHCP reservation settings, or use the machine's hostname instead of IP if your LAN has working DNS.
