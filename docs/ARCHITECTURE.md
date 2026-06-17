# Software Architecture — P&ID Intelligence System

> **Version:** 1.0 | **Status:** Approved | **Date:** 2026-06-04

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          User (Browser)                             │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────────────────────┐
│                     Streamlit Frontend  :8501                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Dashboard│ │  Upload  │ │  Search  │ │  Graph   │ │   Chat   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ REST (httpx)
┌─────────────────────────▼───────────────────────────────────────────┐
│                    FastAPI Backend  :8000                            │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                     API Routes (v1)                           │  │
│  │  /units  /upload  /search  /graph  /query                    │  │
│  └────────────────────────┬─────────────────────────────────────┘  │
│                           │                                         │
│        ┌──────────────────┼──────────────────┐                     │
│        │                  │                  │                     │
│  ┌─────▼──────┐   ┌───────▼──────┐   ┌──────▼──────┐             │
│  │  Vision    │   │   Agents     │   │    Graph    │             │
│  │  Service   │   │  (LangChain) │   │   Builder   │             │
│  │            │   │              │   │ (NetworkX)  │             │
│  │ Gemini API │   │ Coordinator  │   │             │             │
│  │ pdf2image  │   │ P&ID Agent   │   │ unit graphs │             │
│  └─────┬──────┘   │ Graph Agent  │   │ cross-unit  │             │
│        │          │ Doc Agent    │   │ graph       │             │
│        │          │ Incident Agt │   └──────┬──────┘             │
│        │          └───────┬──────┘          │                     │
│        │                  │                  │                     │
│  ┌─────▼──────────────────▼──────────────────▼──────────────────┐  │
│  │                     Data Layer                                │  │
│  │                                                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │  PostgreSQL  │  │   ChromaDB   │  │  Filesystem       │  │  │
│  │  │  :5432       │  │  (embedded)  │  │  data/pids/       │  │  │
│  │  │              │  │              │  │  data/manuals/    │  │  │
│  │  │ units        │  │ {unit}_equip │  │  data/graphs/     │  │  │
│  │  │ pid_docs     │  │ {unit}_docs  │  │  chroma_db/       │  │  │
│  │  │ equip_tags   │  │              │  │                   │  │  │
│  │  │ connections  │  │              │  │                   │  │  │
│  │  │ audit_log    │  │              │  │                   │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
┌─────────────▼──────┐   ┌────────────▼──────────┐
│   Ollama  :11434   │   │   Gemini Flash API     │
│   llama3.2 (chat)  │   │   (vision, free tier)  │
│   nomic-embed-text │   │                        │
└────────────────────┘   └────────────────────────┘
```

---

## 2. Component Responsibilities

### 2.1 Frontend (Streamlit)
- Single-page app with sidebar navigation and unit selector
- All backend calls via `httpx` REST client — no direct DB access
- Session state holds: `selected_unit`, `chat_history`
- Pages: Dashboard, Upload, Search, Graph, Chat, Documents

### 2.2 Backend API (FastAPI)
- Stateless REST API; all state in DB / filesystem
- Async throughout (`asyncio`, `asyncpg`)
- Auto-generated OpenAPI docs at `/docs`
- Routes are thin — delegate to service layer

| Route prefix | Responsibility |
|---|---|
| `/api/v1/units` | CRUD for process units |
| `/api/v1/upload` | Accept PDF uploads, queue processing jobs |
| `/api/v1/search` | Tag search (PostgreSQL + ChromaDB) |
| `/api/v1/graph` | Graph data and traversal |
| `/api/v1/query` | NL query via agent, in-app bug reporting |

### 2.3 Vision Service (`backend/vision/`)
- `pdf2image` converts each PDF page to PNG at 200 DPI
- Each image sent to **Gemini Flash** with structured extraction prompt
- Returns JSON: `{tags[], sheet_number, process_description}`
- Handles: markdown fences in response, JSON parse failures, rate-limit retry (tenacity)

### 2.4 Agent System (`backend/agents/`)

```
User question
      │
      ▼
CoordinatorAgent (Ollama llama3.2)
      │
      ├─ Tool: search_equipment    → GraphBuilder.get_neighbours()
      ├─ Tool: list_equipment_by_type → GraphBuilder.get_nodes_by_type()
      ├─ Tool: trace_process_path  → GraphBuilder.find_path()
      ├─ Tool: find_impact         → GraphBuilder.get_neighbours(depth=3)
      └─ Tool: search_sop          → RAGEngine.search_documents()
      │
      ▼
Formatted answer
```

- Built on LangChain `create_tool_calling_agent` + `AgentExecutor`
- One agent instance per request (stateless)
- Chat history passed in for multi-turn conversations
- Max 5 iterations to prevent runaway loops

### 2.5 Graph Builder (`backend/graph/`)
- `NetworkX.DiGraph` per unit (directed graph)
- Nodes: equipment tags with `{unit, tag_type, description, ...}` attributes
- Edges: process connections with `{connection_type, line_number}` attributes
- Persisted as JSON via `nx.node_link_data()` to `data/graphs/{unit}_graph.json`
- Cross-unit connections in separate `cross_unit_graph.json`
- Loaded lazily on first access, cached in memory during process lifetime

### 2.6 RAG Engine (`backend/rag/`)
- **ChromaDB PersistentClient** (embedded — no separate server)
- Two collection types per unit:
  - `{unit}_equipment` — equipment tag descriptions for semantic search
  - `{unit}_docs` — SOP/manual text chunks
- Embeddings via **Ollama `nomic-embed-text`** (local, free)
- Cosine similarity search

---

## 3. Data Flow — PDF Processing

```
1. User uploads PDF(s) for unit CDU
         │
2. FastAPI saves to data/pids/{unit_id}/{filename}.pdf
         │
3. BackgroundTask creates processing_job record (status=queued)
         │
4. PIDExtractor.pdf_to_images() → PNG per page at 200 DPI
         │
5. For each page image:
   └─ PIDExtractor.extract_from_image() → Gemini Flash API
         │
         ├─ Returns: {tags[], sheet_number, process_description}
         │
6. For each tag in response:
   ├─ Upsert into PostgreSQL equipment_tags
   ├─ Add node to NetworkX unit graph
   └─ Build connected_to edges in graph
         │
7. Save NetworkX graph to data/graphs/{unit}_graph.json
         │
8. Embed tag descriptions → ChromaDB {unit}_equipment collection
         │
9. Update pid_document.processing_status = 'completed'
        Update processing_job.status = 'completed'
```

---

## 4. Data Flow — NL Query

```
1. User asks: "What pumps are upstream of the fractionator?"
   with unit_id = CDU_uuid
         │
2. /api/v1/query/nl resolves unit_id → unit_name = "CDU"
         │
3. CoordinatorAgent.run(question, unit_name="CDU")
         │
4. LLM (Ollama) reasons → calls tool: list_equipment_by_type("pump")
         │
5. GraphBuilder.get_nodes_by_type("CDU", "pump") → [P-101, P-102, ...]
         │
6. LLM reasons further → calls tool: find_impact("fractionator_inlet")
         │
7. GraphBuilder.get_neighbours("CDU", "fractionator_inlet", depth=3)
         │
8. LLM synthesises answer → returns to API
         │
9. NLQueryResponse returned to frontend → rendered in chat
```

---

## 5. Unit Isolation Model

Each process unit (CDU, VDU, HCU, etc.) is fully isolated:

| Storage | Per-Unit Resource |
|---|---|
| PostgreSQL | Rows filtered by `unit_id` FK |
| ChromaDB | `{unit}_equipment` + `{unit}_docs` collections |
| NetworkX | `data/graphs/{unit}_graph.json` |
| Filesystem | `data/pids/{unit_id}/` |

Cross-unit connections are tracked separately:
- `cross_unit_connections` table in PostgreSQL
- `data/graphs/cross_unit_graph.json` (single shared graph)
- Only loaded when user enables "Show cross-unit connections"

---

## 6. Environment Configuration

| Environment | Config | Notes |
|---|---|---|
| Development | `docker-compose.yml` + `.env` | Hot-reload, debug logs |
| Staging | `docker-compose.staging.yml` | No hot-reload, INFO logs |
| Test | `pytest` fixtures mock external APIs | In-memory / tmp dirs |

---

## 7. Security Considerations (Demo Scope)

- No authentication (deferred to V2)
- `SECRET_KEY` env var used for any future token signing
- API keys in `.env` only — never committed
- CORS restricted to Streamlit origin
- File uploads: type-checked (PDF only), size-limited (50 MB)
- SQL: SQLAlchemy ORM only — no raw string queries
