# P&ID Intelligence System — Brainstorming

> **Status:** Draft | **Phase:** 1 — Ideation | **Date:** 2026-06-04

---

## 1. Problem Space

### Current Reality for Process Engineers
- P&ID drawings are static PDFs or large-format paper prints
- Finding a specific instrument tag means manually scanning dozens of sheets
- Tracing a process path (e.g., "where does the feed go after V-101?") requires following lines across multiple drawings
- Impact analysis before a shutdown ("what else stops if P-201 trips?") is done from memory or manual tracing
- SOPs are stored separately in SharePoint/folders — no link to the drawing
- New engineers take months to understand plant topology

### The Core Pain
> Engineers are the search engine. The drawings cannot answer questions.

---

## 2. User Personas

| Persona | Role | Primary Pain | Desired Outcome |
|---|---|---|---|
| **Alex** | Process Engineer | Traces process paths manually across 30 sheets | "Show me everything downstream of V-101" |
| **Priya** | Safety Engineer | Impact analysis before any MOC | "What instruments are on this loop?" |
| **Rajan** | Operations Manager | Correlating alarms to equipment | "Which SOP covers this valve?" |
| **Sam** | Maintenance Technician | Finding all instruments on a pump | "List all instruments on P-201" |
| **Neha** | New Graduate Engineer | Plant topology unfamiliar | "Explain the CDU distillation column circuit" |

---

## 3. Feature Brainstorm

### Core (MVP)
- [ ] Unit-wise P&ID PDF upload (CDU, VDU, HCU, etc.)
- [ ] Auto-extraction of equipment tags from P&ID pages (via Gemini Vision)
- [ ] Symbol recognition: pumps, vessels, valves, exchangers, instruments
- [ ] Knowledge graph per unit (NetworkX)
- [ ] Cross-unit piping connection tracking
- [ ] Natural language queries: "List all pumps in CDU"
- [ ] Equipment tag search with details
- [ ] Process path tracing: upstream/downstream neighbours
- [ ] Graph visualisation (interactive)
- [ ] SOP/manual PDF upload and linking to equipment

### Extended (V2)
- [ ] Impact analysis: "If P-101 fails, what else is affected?"
- [ ] Instrument loop diagrams from NL description
- [ ] Alarm rationalisation support
- [ ] Maintenance recommendation based on equipment history
- [ ] Incident reporting and correlation with P&ID graph
- [ ] Export knowledge graph to Excel / JSON
- [ ] Multi-user access with unit-level permissions

### Future / Advanced
- [ ] Live sensor data overlay on graph
- [ ] Anomaly detection (sensor + graph reasoning)
- [ ] Digital twin integration
- [ ] Predictive maintenance scoring
- [ ] 3D plant model integration
- [ ] Regulatory compliance checker against P&IDs

---

## 4. Technical Approach Exploration

### Vision Extraction Strategy
**Option A: Gemini Flash (free tier)**
- Send each P&ID page as image to Gemini Vision
- Prompt it to extract: tags, equipment types, connections, line numbers
- Pros: High accuracy on complex drawings, no local GPU needed
- Cons: API rate limits on free tier, data leaves local environment

**Option B: LLaVA via Ollama (local)**
- Run LLaVA 7B/13B locally
- Pros: Fully offline, no API cost
- Cons: Lower accuracy on dense P&ID drawings, needs 8–16 GB VRAM

**Decision: Gemini Flash** — better accuracy for complex engineering drawings; free tier is sufficient for demo

### Graph Strategy
**Option A: NetworkX (Python)**
- In-memory graph, serialised to JSON
- One graph file per unit + one cross-unit graph
- Pros: Zero infrastructure, fast for demo scale (<10K nodes)
- Cons: Not persistent across restarts without explicit save

**Option B: Neo4j Community**
- Full graph database, Cypher query language
- Pros: Production-grade, powerful graph queries
- Cons: Extra Docker container, more setup

**Decision: NetworkX** — perfect for demo scale; can migrate to Neo4j if needed

### NL Query Strategy
- LangChain agent with Ollama (Llama 3.2) as reasoning backbone
- Tool-calling pattern: coordinator routes query → specialised agents use graph/vector tools
- ChromaDB for semantic search (per-unit collections)
- Graph traversal exposed as LangChain tools

---

## 5. Data Flow (High Level)

```
PDF Upload
    │
    ▼
Page Extraction (pdf2image)
    │
    ├──► Page images (PNG per page)
    │
    ▼
Gemini Vision per page
    │
    ├──► Extracted tags + symbols + connections (JSON)
    │
    ▼
Tag Normalisation + Deduplication
    │
    ├──► PostgreSQL  (equipment_tags, pid_documents)
    ├──► ChromaDB    (unit collection — semantic search)
    └──► NetworkX    (unit graph — relationship traversal)

NL Query
    │
    ▼
Coordinator Agent (Ollama)
    │
    ├──► P&ID Agent    → graph traversal
    ├──► Graph Agent   → NetworkX queries
    ├──► Document Agent→ ChromaDB RAG on SOPs
    └──► Incident Agent→ incident lookup
    │
    ▼
Response Agent → formatted answer
```

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Gemini Vision misses tags on complex drawings | Medium | High | Post-processing validation, confidence scores, manual correction UI |
| Ollama too slow on CPU-only machines | High | Medium | Allow configuring smaller model (Qwen 0.5B fallback) |
| Gemini free tier rate limits (15 RPM) | High | Medium | Queue-based processing with backoff; batch pages |
| Cross-unit graph gets too large | Low | Medium | Lazy loading per unit; only load cross-unit on demand |
| PDF quality too low for OCR | Medium | High | Pre-processing: contrast enhance, deskew via OpenCV |

---

## 7. Success Metrics (Demo)

| Metric | Target |
|---|---|
| Tag extraction accuracy | > 85% precision on clear P&IDs |
| Query response time | < 5 seconds for NL query |
| Graph build time per P&ID page | < 30 seconds |
| SOP retrieval relevance | Top-1 relevant SOP in 80% of queries |
| Uptime (local Docker) | N/A — demo use |

---

## 8. Open Questions (Resolved)

| Question | Decision |
|---|---|
| Unit list fixed or dynamic? | Dynamic — users create unit names |
| One PDF or many per unit? | Many (10–50 sheets per unit) |
| Cross-unit connections? | Yes — tracked in separate table + graph |
| Graph DB? | NetworkX (JSON-persisted) |
| LLM? | Ollama (chat) + Gemini Flash (vision) |
| SQL DB? | PostgreSQL |
| Vector DB? | ChromaDB (per-unit collections) |
| Deployment? | Local Docker Compose |
