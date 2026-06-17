# How to Run — P&ID Intelligence System

Step-by-step guide to get the application running on a Windows machine from scratch.

---

## Prerequisites

Install these before running the setup script:

| Software | Version | Download |
|---|---|---|
| Python | 3.11 or newer | https://python.org (check "Add to PATH" during install) |
| Node.js | 18 LTS or newer | https://nodejs.org |
| PostgreSQL | 15 or newer | https://postgresql.org |
| Poppler | latest | https://github.com/oschwartz10612/poppler-windows/releases — extract to `C:\poppler\` |
| Git | any | https://git-scm.com |

Verify everything installed correctly:

```cmd
python --version
node --version
psql --version
```

---

## Step 1 — Clone the repository

```cmd
git clone https://github.com/DigantaKrborah/pid-intelligence-system.git
cd pid-intelligence-system
```

Or download and extract the ZIP from GitHub.

---

## Step 2 — Create the PostgreSQL database

Open pgAdmin (installed with PostgreSQL) or run in Command Prompt:

```cmd
psql -U postgres
```

Then in the PostgreSQL shell:

```sql
CREATE DATABASE pid_system;
CREATE USER pid_user WITH PASSWORD 'your_password_here';
GRANT ALL PRIVILEGES ON DATABASE pid_system TO pid_user;
\q
```

---

## Step 3 — Run the setup script

Double-click `setup_venv.bat` from the project root. This will:

1. Create a Python virtual environment in `.venv\`
2. Install all Python packages from `backend\requirements.txt`
3. Install all frontend npm packages from `frontend\package.json`
4. Copy `backend\.env.example` → `backend\.env` (if not already present)
5. Create the database schema and seed data

---

## Step 4 — Edit your environment file

Open `backend\.env` in a text editor and fill in:

```env
# Your PostgreSQL connection string
DATABASE_URL=postgresql://pid_user:your_password_here@localhost:5432/pid_system

# Generate a random secret key — run this in Python:
# python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=paste_generated_key_here
```

The other values have safe defaults for local development.

---

## Step 5 — Start the application

Double-click `start_all.bat` from the project root.

This opens two separate windows:
- **P&ID Backend** — FastAPI server on port 8000
- **P&ID Frontend** — React dev server on port 5173

The script also prints the URL to share with teammates on your network.

---

## Step 6 — Log in

Open `http://localhost:5173` in your browser.

Default admin credentials (set by the seed script):

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `Admin@123` |

**Change this password** on first login via Settings → User Management.

---

## Individual launchers

| Script | What it starts |
|---|---|
| `start_all.bat` | Both backend and frontend (recommended) |
| `start_backend.bat` | FastAPI backend only |
| `start_frontend.bat` | React frontend only |
| `setup_venv.bat` | First-time setup (run once) |

---

## Application structure at a glance

```
http://localhost:5173/         → Login page
http://localhost:5173/units    → Process units (CDU, VDU, etc.)
http://localhost:5173/drawings → Upload and manage P&ID drawings
http://localhost:5173/tags     → Search extracted equipment tags
http://localhost:5173/documents→ Upload operating manuals & SOPs
http://localhost:5173/settings → LLM provider config (admin only)
http://localhost:5173/audit    → System audit log (admin only)

http://localhost:8000/docs     → Interactive API documentation
```

---

## Workflow — from PDF to queryable data

```
1. Create a Process Unit (e.g. "CDU — Crude Distillation Unit")
2. Upload P&ID PDF drawings for that unit
3. Run AI extraction on each drawing
   → The system calls your configured LLM (Claude / GPT-4o / Gemini)
   → Extracts equipment tags, instrument tags, line specs, connectivity
4. Search tags — type a tag number or description in the search bar
5. Upload manuals/SOPs for document-based Q&A (optional)
```

---

## Configuring the AI (LLM) provider

Go to **Settings → LLM Configuration**. Enter your API key for one of:

| Provider | Key source |
|---|---|
| Claude (Anthropic) | https://console.anthropic.com |
| OpenAI GPT-4o | https://platform.openai.com |
| Google Gemini | https://aistudio.google.com |

The API key is never stored in the database — only the last 4 characters are saved as a hint.

---

## Stopping the application

Close the two server windows (**P&ID Backend** and **P&ID Frontend**).

The `start_all.bat` launcher window can be closed at any time — it does not stop the servers.

---

## Updating the application

```cmd
git pull
setup_venv.bat     ← re-runs pip install and npm install to pick up new packages
```

---

## Troubleshooting

**"Python is not installed or not on PATH"**  
→ Reinstall Python and check "Add Python to PATH" during setup.

**"pip install failed"**  
→ Check `backend\requirements.txt` exists. Try: `.venv\Scripts\pip install -r backend\requirements.txt`

**"Database setup failed"**  
→ Check PostgreSQL is running. Verify `DATABASE_URL` in `backend\.env` has the right password.

**"Cannot connect to http://localhost:8000"**  
→ The backend is not running. Start it with `start_backend.bat`.

**Login says "Incorrect username or password"**  
→ Run `setup_venv.bat` again to re-seed the database, or check `db\seed.sql`.

**"CORS error" in browser console**  
→ The frontend URL is not in CORS_ORIGINS. See `docs\NETWORK_SETUP.md`.

---

## For network access (multiple users)

See `docs\NETWORK_SETUP.md` for firewall rules, static IP setup, auto-start, and daily backups.
