# P&ID Intelligence System

AI-powered tool to extract, query, and analyse Piping and Instrumentation Diagrams (P&IDs)
for process engineering teams at Numaligarh Refinery Ltd.

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Frontend   | React 18 + Tailwind CSS (Vite, port 5173) |
| Backend    | Python 3.11 + FastAPI (port 8000)       |
| Database   | PostgreSQL 15 (local)                   |
| File Store | Local disk — `E:/PID_Reader/uploads/`   |
| AI Engine  | Claude API / OpenAI GPT-4o / Google Gemini (configurable) |
| Auth       | JWT-based login                         |
| OS         | Windows 11                              |

## Folder Structure

```
/backend        → Python FastAPI application
/frontend       → React 18 application
/db             → SQL schema and migration files
/uploads        → All uploaded files (P&IDs, manuals, SOPs) — LOCAL ONLY
/docs           → Documentation
```

## Quick Start

See `status.md` for current build progress.
