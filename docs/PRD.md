# Product Requirements Document — P&ID Intelligence System (MVP)

> **Version:** 1.0 | **Status:** Approved for MVP | **Date:** 2026-06-04

---

## 1. Product Summary

An AI-powered web application that converts static P&ID (Piping & Instrumentation Diagram) PDF drawings into a searchable, queryable knowledge graph. Engineers select their process unit (CDU, VDU, HCU, etc.), upload P&ID sheets, and interact with the plant data via natural language.

**One-line pitch:** Ask your P&IDs a question — in plain English.

---

## 2. MVP Goals

| Goal | Measure |
|---|---|
| Upload P&IDs unit-wise | User can create a unit, upload 1–50 PDF sheets, see processing status |
| Extract equipment tags | ≥ 85% precision on clearly scanned P&IDs |
| Build knowledge graph | Nodes = equipment; edges = process connections (incl. cross-unit) |
| Natural language queries | Answer 5 core query types (see §5) in < 5 seconds |
| Process graph visualisation | Interactive node-link graph per unit |
| SOP linking | Upload a document, link to a tag, retrieve via NL query |

### Non-Goals (deferred to V2)
- Live sensor integration
- Anomaly detection
- Mobile app
- Multi-user authentication / RBAC
- Export to Excel/CAD

---

## 3. Users

**Primary:** Process engineer at a refinery or chemical plant — familiar with P&ID symbology, ISA standards, and unit operations.

**Secondary:** New graduate engineer learning plant topology.

---

## 4. Core User Journeys

### J1 — First-time Setup
1. Open app → see empty dashboard
2. Click **"+ New Unit"** → enter unit name (e.g., `CDU`) and description
3. Upload 5 P&ID PDF files for CDU
4. System processes each page via Gemini Vision → extracts tags
5. Graph is built; dashboard shows tag count and graph stats

### J2 — Equipment Search
1. Select unit `CDU` from sidebar
2. Type tag `P-101` in search bar
3. See: tag type (Centrifugal Pump), connected instruments, upstream/downstream lines
4. Click a neighbour → navigate graph

### J3 — Natural Language Query
1. Select unit `HCU` → open Chat tab
2. Ask: *"What instruments are monitoring the reactor feed?"*
3. System returns: list of FIC, TIC, PIC tags with their descriptions
4. Ask: *"Show me the process path from V-201 to the fractionator"*
5. System returns: ordered path with intermediate equipment

### J4 — Cross-Unit Impact Analysis
1. Select **All Units** view
2. Ask: *"If the CDU main column overhead pump fails, what downstream units are affected?"*
3. System traverses cross-unit graph and returns affected units and equipment

### J5 — SOP Retrieval
1. Select unit `VDU`
2. Upload `VDU_Startup_SOP.pdf`
3. Ask: *"What is the startup procedure for the VDU vacuum system?"*
4. System returns: relevant SOP section + linked equipment tags

---

## 5. Functional Requirements

### FR-01 Unit Management
- Create unit with name (free text) + optional description
- List all units with stats (doc count, tag count, last updated)
- Archive a unit
- Units are isolated: each has its own graph + vector collection

### FR-02 P&ID Upload & Processing
- Accept PDF files (single or batch, up to 50 files per unit)
- Convert each page to image (300 DPI)
- Send each page image to Gemini Flash Vision with structured extraction prompt
- Extract: equipment tags, tag types, connections, line numbers
- Show per-file processing status: queued / processing / completed / failed
- Store extracted data in PostgreSQL + ChromaDB + NetworkX graph

### FR-03 Knowledge Graph
- Each unit has its own NetworkX graph (JSON-persisted)
- Nodes: equipment tag, type, unit, source document, page number
- Edges: process connection type (pipeline, signal, utility)
- Cross-unit connections stored in separate cross-unit graph
- Graph is rebuilt incrementally as new PDFs are processed

### FR-04 Equipment Search
- Search by tag name (exact + fuzzy)
- Filter by: unit, equipment type (pump, valve, vessel, instrument, exchanger)
- Result card: tag, type, unit, connected neighbours, source P&ID sheet

### FR-05 Natural Language Query (5 core types)
| Query Type | Example |
|---|---|
| List by type | "List all control valves in CDU" |
| Equipment details | "Tell me about TIC-301" |
| Path tracing | "What is the process path from P-101 to E-201?" |
| Impact analysis | "What fails if V-101 is isolated?" |
| SOP retrieval | "What is the procedure for depressurising HCU reactor?" |

### FR-06 Graph Visualisation
- Interactive node-link diagram (streamlit-agraph or Plotly)
- Colour-code nodes by equipment type
- Click node → show details panel
- Toggle: single unit view / cross-unit view
- Zoom, pan, search-highlight

### FR-07 Document Management (SOPs / Manuals)
- Upload PDF/DOCX documents, assign to a unit
- Extract text, chunk, embed into ChromaDB per-unit collection
- Retrieve via semantic search or NL query

### FR-08 Bug Reporting (in-app)
- "Report Issue" button accessible from every page
- Opens GitHub Issue pre-filled with: page, unit context, description field
- Issues labelled `bug` automatically

---

## 6. Non-Functional Requirements

| Requirement | Target |
|---|---|
| P&ID page processing time | < 30 sec per page (Gemini API) |
| NL query response | < 5 seconds |
| Graph load time | < 2 seconds for ≤ 500 nodes |
| PDF file size limit | 50 MB per file |
| Concurrent uploads | 3 files processed in parallel |
| Local Docker resource | ≤ 4 GB RAM total |

---

## 7. Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | Streamlit | Fast to build, Python-native, free |
| Backend API | FastAPI | Async, auto-docs, lightweight |
| Vision LLM | Gemini Flash 1.5 (free tier) | Best accuracy for P&ID drawings |
| Chat LLM | Ollama + Llama 3.2 | Local, free, good reasoning |
| Embeddings | Ollama nomic-embed-text | Local, free |
| Vector DB | ChromaDB (embedded) | No extra server, per-unit collections |
| Graph | NetworkX + JSON | Zero infrastructure, demo-scale |
| SQL DB | PostgreSQL 16 (Docker) | Metadata, tags, audit log |
| Agent Framework | LangChain | Tool-calling, agent orchestration |
| CI/CD | GitHub Actions | Free for public repos |
| Containers | Docker Compose | Local dev + staging |

---

## 8. Data Model Summary

```
Unit (1) ──────── (N) PID_Document
Unit (1) ──────── (N) Equipment_Tag
Unit (1) ──────── (N) SOP_Document
Equipment_Tag (N) ── (N) Equipment_Tag  [via connections table + NetworkX edges]
Cross-unit: Equipment_Tag in Unit A ── Equipment_Tag in Unit B  [cross_unit_connections]
```

---

## 9. MVP Milestones

| Milestone | Deliverable |
|---|---|
| M0 — Foundation | Repo, CI/CD, Docker Compose, DB schema, .env setup |
| M1 — Ingestion | PDF upload → Gemini Vision → tag extraction → PostgreSQL |
| M2 — Graph | NetworkX graph build, JSON persistence, cross-unit connections |
| M3 — Vector | ChromaDB indexing for equipment + SOPs |
| M4 — API | FastAPI routes for all FR-01 to FR-07 |
| M5 — Frontend | Streamlit UI with all 5 journeys working |
| M6 — Agents | Coordinator + 4 specialist agents with LangChain |
| M7 — QA | Unit tests, integration tests, bug reporting wired up |
