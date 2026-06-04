# Changelog

All notable changes to this project will be documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [Unreleased]

### Added
- Initial project scaffold following SDLC process
- `BRAINSTORM.md` — problem space analysis, personas, feature ideation, risk analysis
- `PRD.md` — MVP product requirements, user journeys, functional requirements, milestones
- `ARCHITECTURE.md` — system architecture, component responsibilities, data flow diagrams
- `DATABASE_DESIGN.md` — PostgreSQL schema, ChromaDB collections, NetworkX graph schema
- `CLAUDE_DESIGN_PROMPT.md` — detailed prompt for Claude Design UI mockups
- `CLAUDE.md` — project rules file for AI-assisted development
- FastAPI backend skeleton with routes for units, upload, search, graph, query
- Streamlit frontend with 5 pages: Dashboard, Upload, Search, Graph, Chat, Documents
- `GraphBuilder` — NetworkX-based per-unit graph with cross-unit support
- `PIDExtractor` — Gemini Flash Vision P&ID tag extraction with retry logic
- `RAGEngine` — ChromaDB per-unit collections with Ollama embeddings
- `CoordinatorAgent` — LangChain tool-calling agent over graph + RAG
- PostgreSQL schema (`docker/init.sql`) with 8 tables
- Docker Compose for local development and staging
- GitHub Actions CI: lint (ruff + black) + unit tests with coverage
- GitHub Issue templates: bug report, feature request
- PR template with checklist
- In-app bug reporting via GitHub Issues API (`POST /api/v1/query/bug`)
- Unit test suite: `test_graph.py`, `test_vision.py`, `test_api.py`
