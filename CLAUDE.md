# CLAUDE.md — P&ID Intelligence System

This file governs how Claude Code (and any AI assistant) should behave when working in this repository.

---

## Project Overview

AI-powered tool to convert P&ID PDF drawings into a queryable knowledge graph. Engineers select a **process unit** (CDU, VDU, HCU, etc.), upload P&ID PDFs, and query equipment data via natural language.

**Phase:** MVP development | **Environment:** Local Docker Compose

---

## Architecture Rules

### Unit-Wise Isolation
- Every unit has its own: ChromaDB collection, NetworkX graph JSON, PostgreSQL rows
- Never query across units unless the user explicitly requests cross-unit analysis
- ChromaDB collection naming: `{unit_name_lower}_equipment`, `{unit_name_lower}_docs`
- Graph file naming: `data/graphs/{unit_name_lower}_graph.json`
- Cross-unit graph: `data/graphs/cross_unit_graph.json`

### LLM Assignment
- **Vision tasks** (P&ID image analysis): always use Gemini Flash (`gemini-1.5-flash`) — never Ollama for images
- **Chat / reasoning**: always use Ollama (`llama3.2` default, configurable via `OLLAMA_CHAT_MODEL`)
- **Embeddings**: always use Ollama (`nomic-embed-text`) — never a paid embedding API

### Database Rules
- **PostgreSQL**: metadata only — units, documents, equipment tags, audit log, processing jobs
- **ChromaDB**: embeddings only — equipment descriptions, SOP chunks
- **NetworkX**: graph structure only — nodes and edges, serialised to JSON
- Never store raw PDF content or images in any database — filesystem only (`data/pids/`, `data/manuals/`)

---

## Code Style

### Python
- Python 3.11+
- Type hints on all function signatures
- Pydantic models for all API request/response schemas
- `async`/`await` throughout FastAPI routes
- No print statements — use `loguru` logger (`from loguru import logger`)
- Max line length: 100 characters

### File Organisation
```
backend/
  api/routes/      ← FastAPI route handlers (thin, delegate to services)
  agents/          ← LangChain agents (coordinator + specialists)
  graph/           ← NetworkX graph operations
  rag/             ← ChromaDB + retrieval logic
  vision/          ← Gemini Vision calls, PDF processing
  db/              ← SQLAlchemy models + repositories
  models/          ← Pydantic schemas (request/response)
  config.py        ← All config via pydantic-settings, no hardcoded values
```

### No Hardcoded Values
- All configuration through `.env` + `backend/config.py` (pydantic-settings)
- Never hardcode API keys, URLs, model names, or directory paths in source files

---

## Testing Rules

- **Unit tests** in `tests/unit/` — mock all external APIs (Gemini, Ollama, PostgreSQL)
- **Integration tests** in `tests/integration/` — use test Docker containers
- Test file naming: `test_{module_name}.py`
- Every new function needs at least one happy-path test
- Coverage target: ≥ 70% for `backend/` (checked in CI)
- Use `pytest` + `pytest-asyncio` for async tests

---

## Git & SDLC Rules

### Branching Strategy (Trunk-Based)
- `main` — always deployable; protected branch
- `feature/{short-description}` — new features
- `fix/{short-description}` — bug fixes
- `chore/{short-description}` — tooling, deps, docs

### Commit Message Format
```
type(scope): short description

Types: feat | fix | chore | docs | test | refactor | perf
Scope: api | agents | graph | vision | rag | frontend | db | ci

Examples:
feat(vision): extract equipment tags from P&ID page via Gemini
fix(graph): handle missing cross-unit edge on serialisation
test(api): add integration test for unit creation endpoint
```

### PR Rules
- Link the GitHub Issue number in the PR description
- CI must pass before merge (lint + tests)
- Keep PRs focused — one feature or fix per PR

---

## Environment Rules

| File | Purpose |
|---|---|
| `.env` | Local development (gitignored) |
| `.env.example` | Template — always keep in sync with `.env` |
| `docker-compose.yml` | Local dev stack |
| `docker-compose.staging.yml` | Staging overrides |

Never commit `.env` files. Never log secrets.

---

## Bug Reporting

All bugs go to GitHub Issues with the `bug` label. Use the bug report template at `.github/ISSUE_TEMPLATE/bug_report.yml`. For in-app reporting, the frontend calls `POST /api/v1/bugs` which creates a GitHub Issue via the GitHub API.

---

## What NOT To Do

- Do not add Neo4j unless explicitly asked — we use NetworkX
- Do not use OpenAI or Anthropic APIs — Ollama + Gemini free tier only
- Do not add authentication/RBAC — deferred to V2
- Do not process files larger than 50 MB
- Do not modify `docker-compose.prod.yml` without explicit instruction
- Do not run `git push --force` on `main`
