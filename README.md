# P&ID Intelligence System

AI-powered tool that transforms static P&ID (Piping & Instrumentation Diagram) drawings into a searchable knowledge graph. Engineers select a process unit, upload P&ID PDFs, and query equipment data in plain English.

---

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama](https://ollama.ai) installed locally
- A free [Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Clone & configure
```bash
git clone https://github.com/YOUR_USERNAME/pid-intelligence-system.git
cd pid-intelligence-system
cp .env.example .env
# Edit .env — add your GEMINI_API_KEY
```

### 2. Pull Ollama models
```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

### 3. Start
```bash
docker compose up -d
```

| Service | URL |
|---|---|
| Frontend (Streamlit) | http://localhost:8501 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

### 4. First use
1. Open http://localhost:8501
2. Click **+ New Unit** → enter `CDU`
3. Go to **Upload P&IDs** → drop your PDF files
4. Wait for processing → then try **Ask a Question**

---

## Architecture

```
Streamlit UI  →  FastAPI  →  Gemini Flash (vision)
                          →  Ollama llama3.2 (chat)
                          →  ChromaDB (vector search)
                          →  NetworkX (graph)
                          →  PostgreSQL (metadata)
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for full details.

---

## Documentation

| Document | Description |
|---|---|
| [`docs/BRAINSTORM.md`](docs/BRAINSTORM.md) | Problem space, personas, feature ideation |
| [`docs/PRD.md`](docs/PRD.md) | MVP product requirements and milestones |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design and data flows |
| [`docs/DATABASE_DESIGN.md`](docs/DATABASE_DESIGN.md) | Schema for all three databases |
| [`docs/CLAUDE_DESIGN_PROMPT.md`](docs/CLAUDE_DESIGN_PROMPT.md) | Prompt for Claude Design UI mockups |
| [`CLAUDE.md`](CLAUDE.md) | Project rules for AI-assisted development |

---

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/unit/ -v

# Lint
ruff check backend/ frontend/ tests/
black --check backend/ frontend/ tests/

# Run backend locally (without Docker)
uvicorn backend.main:app --reload
```

### Branching
- `main` — always deployable
- `feature/{name}` — new features
- `fix/{name}` — bug fixes

### Bug Reporting
Use the **🐛 Report Bug** button in the sidebar, or [open a GitHub Issue](../../issues/new/choose).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Vision LLM | Gemini Flash 1.5 (free tier) |
| Chat LLM | Ollama + Llama 3.2 (local) |
| Vector DB | ChromaDB (embedded) |
| Graph | NetworkX + JSON |
| SQL DB | PostgreSQL 16 |
| Agents | LangChain |
| CI/CD | GitHub Actions |
