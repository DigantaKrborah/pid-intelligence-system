-- Initial PostgreSQL schema for P&ID Intelligence System

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Units ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS units (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    description TEXT,
    status      VARCHAR(20) NOT NULL DEFAULT 'active',  -- active | archived
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── P&ID Documents ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pid_documents (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id           UUID NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    filename          VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500),
    file_path         VARCHAR(1000),
    file_size_bytes   BIGINT,
    page_count        INTEGER,
    processing_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending | queued | processing | extracting | building_graph | completed | failed
    processing_error  TEXT,
    tags_extracted    INTEGER DEFAULT 0,
    metadata          JSONB,
    uploaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at      TIMESTAMPTZ
);

-- ─── Equipment Tags ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS equipment_tags (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id        UUID NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    document_id    UUID REFERENCES pid_documents(id) ON DELETE SET NULL,
    tag            VARCHAR(100) NOT NULL,
    tag_type       VARCHAR(50),
    -- pump | vessel | valve | instrument | exchanger | compressor | line | other
    description    TEXT,
    page_number    INTEGER,
    coordinates    JSONB,           -- {x, y, width, height} in image pixels
    raw_attributes JSONB,           -- any extra attributes Gemini extracted
    confidence     FLOAT,           -- extraction confidence 0.0 – 1.0
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (unit_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_equipment_tags_unit ON equipment_tags(unit_id);
CREATE INDEX IF NOT EXISTS idx_equipment_tags_tag  ON equipment_tags(tag);
CREATE INDEX IF NOT EXISTS idx_equipment_tags_type ON equipment_tags(tag_type);

-- ─── Tag Connections (within a unit) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tag_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_tag_id   UUID NOT NULL REFERENCES equipment_tags(id) ON DELETE CASCADE,
    target_tag_id   UUID NOT NULL REFERENCES equipment_tags(id) ON DELETE CASCADE,
    connection_type VARCHAR(50),    -- pipeline | signal | utility | drain | vent
    line_number     VARCHAR(100),
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Cross-Unit Connections ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cross_unit_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_tag_id   UUID NOT NULL REFERENCES equipment_tags(id) ON DELETE CASCADE,
    target_tag_id   UUID NOT NULL REFERENCES equipment_tags(id) ON DELETE CASCADE,
    source_unit_id  UUID NOT NULL REFERENCES units(id),
    target_unit_id  UUID NOT NULL REFERENCES units(id),
    connection_type VARCHAR(50),
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Engineering Documents (SOPs, Manuals) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS engineering_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id     UUID REFERENCES units(id) ON DELETE SET NULL,  -- NULL = global
    doc_type    VARCHAR(50),    -- SOP | manual | procedure | datasheet | standard
    title       VARCHAR(500),
    filename    VARCHAR(500),
    file_path   VARCHAR(1000),
    page_count  INTEGER,
    indexed     BOOLEAN NOT NULL DEFAULT FALSE,
    chunk_count INTEGER DEFAULT 0,
    metadata    JSONB,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Processing Jobs ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS processing_jobs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   UUID NOT NULL,
    document_type VARCHAR(10) NOT NULL,   -- pid | sop
    status        VARCHAR(20) NOT NULL DEFAULT 'queued',
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    error_message TEXT,
    result_summary JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Incidents ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS incidents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id      UUID REFERENCES units(id),
    title        VARCHAR(500) NOT NULL,
    description  TEXT,
    severity     VARCHAR(20),    -- critical | high | medium | low
    related_tags JSONB,          -- array of tag strings
    status       VARCHAR(20) NOT NULL DEFAULT 'open',   -- open | investigating | resolved
    resolution   TEXT,
    reported_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at  TIMESTAMPTZ
);

-- ─── Audit Log ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action      VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id   UUID,
    details     JSONB,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
