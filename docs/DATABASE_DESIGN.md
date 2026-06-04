# Database Design — P&ID Intelligence System

> **Version:** 1.0 | **Date:** 2026-06-04

---

## 1. Overview — Multi-Database Strategy

| Database | Technology | Role |
|---|---|---|
| **Relational** | PostgreSQL 16 | Metadata, unit registry, equipment tags, audit |
| **Vector** | ChromaDB (embedded) | Semantic embeddings for search and RAG |
| **Graph** | NetworkX + JSON | Process topology, path traversal |
| **Filesystem** | Docker volume | Raw PDFs, page images, graph JSON files |

---

## 2. PostgreSQL Schema

### ER Diagram (text)

```
units
  │
  ├─── pid_documents ──── processing_jobs
  │         │
  │    equipment_tags ─┐
  │         │          │
  │    tag_connections─┘ (within-unit edges)
  │
  ├─── cross_unit_connections (between units)
  │
  ├─── engineering_documents ──── processing_jobs
  │
  └─── incidents
  
audit_log (global, references any entity)
```

### Table: `units`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | `gen_random_uuid()` |
| `name` | VARCHAR(100) UNIQUE | User-defined, e.g. `CDU` |
| `display_name` | VARCHAR(200) | Optional long name |
| `description` | TEXT | |
| `status` | VARCHAR(20) | `active` \| `archived` |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

### Table: `pid_documents`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `unit_id` | UUID FK → units | Cascade delete |
| `filename` | VARCHAR(500) | Stored filename |
| `original_filename` | VARCHAR(500) | As uploaded |
| `file_path` | VARCHAR(1000) | Absolute path on filesystem |
| `file_size_bytes` | BIGINT | |
| `page_count` | INTEGER | |
| `processing_status` | VARCHAR(20) | `pending\|queued\|processing\|extracting\|building_graph\|completed\|failed` |
| `processing_error` | TEXT | Populated on failure |
| `tags_extracted` | INTEGER | Count of tags found |
| `metadata` | JSONB | Sheet numbers, process areas |
| `uploaded_at` | TIMESTAMPTZ | |
| `completed_at` | TIMESTAMPTZ | |

### Table: `equipment_tags`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `unit_id` | UUID FK → units | |
| `document_id` | UUID FK → pid_documents | Nullable (tag may span sheets) |
| `tag` | VARCHAR(100) | e.g. `P-101`, `TIC-301` |
| `tag_type` | VARCHAR(50) | `pump\|vessel\|valve\|instrument\|exchanger\|compressor\|line\|other` |
| `description` | TEXT | Human-readable description |
| `page_number` | INTEGER | Source PDF page |
| `coordinates` | JSONB | `{x, y, width, height}` pixels |
| `raw_attributes` | JSONB | Any extra Gemini-extracted fields |
| `confidence` | FLOAT | Extraction confidence 0.0–1.0 |
| `created_at` | TIMESTAMPTZ | |

**Indexes:** `unit_id`, `tag`, `tag_type`  
**Unique constraint:** `(unit_id, tag)` — one tag per unit

### Table: `tag_connections`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `source_tag_id` | UUID FK → equipment_tags | |
| `target_tag_id` | UUID FK → equipment_tags | |
| `connection_type` | VARCHAR(50) | `pipeline\|signal\|utility\|drain\|vent` |
| `line_number` | VARCHAR(100) | Pipe line tag |
| `description` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

### Table: `cross_unit_connections`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `source_tag_id` | UUID FK → equipment_tags | |
| `target_tag_id` | UUID FK → equipment_tags | |
| `source_unit_id` | UUID FK → units | Denormalised for fast queries |
| `target_unit_id` | UUID FK → units | |
| `connection_type` | VARCHAR(50) | |
| `description` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

### Table: `engineering_documents`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `unit_id` | UUID FK → units | NULL = global document |
| `doc_type` | VARCHAR(50) | `SOP\|manual\|procedure\|datasheet\|standard` |
| `title` | VARCHAR(500) | |
| `filename` | VARCHAR(500) | |
| `file_path` | VARCHAR(1000) | |
| `page_count` | INTEGER | |
| `indexed` | BOOLEAN | False until ChromaDB ingestion done |
| `chunk_count` | INTEGER | Number of text chunks indexed |
| `metadata` | JSONB | |
| `uploaded_at` | TIMESTAMPTZ | |

### Table: `processing_jobs`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `document_id` | UUID | References `pid_documents` or `engineering_documents` |
| `document_type` | VARCHAR(10) | `pid` \| `sop` |
| `status` | VARCHAR(20) | `queued\|processing\|completed\|failed` |
| `started_at` | TIMESTAMPTZ | |
| `completed_at` | TIMESTAMPTZ | |
| `error_message` | TEXT | |
| `result_summary` | JSONB | `{tags_found, pages_processed, ...}` |
| `created_at` | TIMESTAMPTZ | |

### Table: `incidents`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `unit_id` | UUID FK → units | |
| `title` | VARCHAR(500) | |
| `description` | TEXT | |
| `severity` | VARCHAR(20) | `critical\|high\|medium\|low` |
| `related_tags` | JSONB | Array of tag strings, e.g. `["P-101", "V-201"]` |
| `status` | VARCHAR(20) | `open\|investigating\|resolved` |
| `resolution` | TEXT | |
| `reported_at` | TIMESTAMPTZ | |
| `resolved_at` | TIMESTAMPTZ | |

### Table: `audit_log`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `action` | VARCHAR(100) | e.g. `unit.created`, `pid.uploaded`, `tag.extracted` |
| `entity_type` | VARCHAR(50) | `unit\|pid_document\|equipment_tag\|...` |
| `entity_id` | UUID | |
| `details` | JSONB | Action-specific payload |
| `timestamp` | TIMESTAMPTZ | |

---

## 3. ChromaDB Collections

ChromaDB runs embedded (no separate server). Data persisted at `chroma_db/`.

### Collection: `{unit}_equipment`
One per unit (e.g. `cdu_equipment`, `vdu_equipment`).

| Field | Description |
|---|---|
| **id** | Equipment tag string, e.g. `P-101` |
| **document** | `"P-101 — pump — Feed pump for CDU"` |
| **embedding** | `nomic-embed-text` vector (768-dim) |
| **metadata** | `{tag_type, unit, page_number}` |

Used for: fuzzy tag search, "find equipment similar to X".

### Collection: `{unit}_docs`
One per unit (e.g. `cdu_docs`, `hcu_docs`).

| Field | Description |
|---|---|
| **id** | `{doc_id}_{chunk_index}` |
| **document** | Text chunk (512 tokens, 50-token overlap) |
| **embedding** | `nomic-embed-text` vector |
| **metadata** | `{source_filename, page_number, doc_type, unit}` |

Used for: SOP retrieval, "what is the procedure for X?"

**Chunking strategy:** 512 tokens, 50-token overlap, split on paragraph boundaries where possible.

---

## 4. NetworkX Graph Schema

### Per-Unit Graph
File: `data/graphs/{unit_lower}_graph.json`  
Format: `nx.node_link_data()` JSON

**Nodes:**
```json
{
  "id": "P-101",
  "unit": "CDU",
  "tag_type": "pump",
  "description": "Feed pump",
  "document_id": "uuid...",
  "page_number": 3
}
```

**Edges:**
```json
{
  "source": "P-101",
  "target": "E-101",
  "connection_type": "pipeline",
  "line_number": "4\"-CS-001"
}
```

### Cross-Unit Graph
File: `data/graphs/cross_unit_graph.json`

Same schema. Nodes include `unit` attribute to identify origin. Loaded only when cross-unit view is requested.

---

## 5. Filesystem Layout

```
data/
├── pids/
│   └── {unit_id}/          ← UUID of the unit
│       ├── P&ID-CDU-001.pdf
│       ├── P&ID-CDU-001_pages/
│       │   ├── page_001.png
│       │   ├── page_002.png
│       │   └── ...
│       └── P&ID-CDU-002.pdf
│
├── manuals/
│   └── {unit_id}/
│       └── CDU_Startup_SOP.pdf
│
└── graphs/
    ├── cdu_graph.json
    ├── vdu_graph.json
    ├── hcu_graph.json
    └── cross_unit_graph.json

chroma_db/                  ← ChromaDB persistent storage
├── cdu_equipment/
├── cdu_docs/
├── vdu_equipment/
└── ...
```

---

## 6. Data Lifecycle

| Event | PostgreSQL | ChromaDB | NetworkX | Filesystem |
|---|---|---|---|---|
| Unit created | INSERT units | Create collections | — | mkdir |
| PDF uploaded | INSERT pid_documents | — | — | Save file |
| Processing started | UPDATE status=processing | — | — | Extract pages |
| Tags extracted | INSERT equipment_tags | UPSERT embeddings | Add nodes/edges | — |
| PDF processed | UPDATE status=completed | — | Save JSON | — |
| SOP uploaded | INSERT engineering_documents | — | — | Save file |
| SOP indexed | UPDATE indexed=true | UPSERT chunks | — | — |
| Unit archived | UPDATE status=archived | Collections kept | Graph kept | Files kept |
