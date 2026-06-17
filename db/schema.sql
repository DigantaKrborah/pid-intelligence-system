-- ============================================================
-- P&ID Intelligence System — PostgreSQL Schema
-- Organization: Numaligarh Refinery Ltd
-- ============================================================

-- Enable UUID generation (required for gen_random_uuid())
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TABLE 1: organizations
-- One row per organization (built for future multi-org scale)
-- ============================================================
CREATE TABLE organizations (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_name    VARCHAR(200) NOT NULL,
  created_at  TIMESTAMP DEFAULT now()
);

-- ============================================================
-- TABLE 2: users
-- Login accounts for the application
-- ============================================================
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        UUID NOT NULL REFERENCES organizations(id),
  username      VARCHAR(50) UNIQUE NOT NULL,
  full_name     VARCHAR(100) NOT NULL,
  email         VARCHAR(150) UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          VARCHAR(20) NOT NULL DEFAULT 'viewer'
                CHECK (role IN ('admin', 'operator', 'viewer')),
  is_active     BOOLEAN DEFAULT true,
  last_login    TIMESTAMP,
  created_at    TIMESTAMP DEFAULT now(),
  updated_at    TIMESTAMP DEFAULT now()
);

-- ============================================================
-- TABLE 3: process_units
-- A unit is like CDU, VDU, HCU, MSP, H2U, etc.
-- ============================================================
CREATE TABLE process_units (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      UUID NOT NULL REFERENCES organizations(id),
  unit_code   VARCHAR(20) NOT NULL,   -- e.g. CDU, VDU, HCU
  unit_name   VARCHAR(200) NOT NULL,  -- e.g. Crude Distillation Unit
  description TEXT,
  is_active   BOOLEAN DEFAULT true,
  created_at  TIMESTAMP DEFAULT now(),
  UNIQUE (org_id, unit_code)
);

-- ============================================================
-- TABLE 4: pid_drawings
-- One row per P&ID drawing sheet uploaded
-- ============================================================
CREATE TABLE pid_drawings (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id             UUID NOT NULL REFERENCES process_units(id),
  drawing_number      VARCHAR(100) NOT NULL,  -- e.g. NRL-CDU-PID-001
  drawing_title       VARCHAR(300),
  revision            VARCHAR(20),            -- e.g. Rev 3, R3
  sheet_number        VARCHAR(20),            -- e.g. Sheet 1 of 5
  original_filename   VARCHAR(300) NOT NULL,
  stored_filepath     TEXT NOT NULL,          -- full path in /uploads/pid_drawings/
  file_type           VARCHAR(10) NOT NULL    -- pdf, jpg, png, tiff
                      CHECK (file_type IN ('pdf','jpg','png','tiff','jpeg')),
  total_pages         INTEGER DEFAULT 1,
  upload_status       VARCHAR(20) DEFAULT 'uploaded'
                      CHECK (upload_status IN ('uploaded','processing','completed','failed')),
  uploaded_by         UUID REFERENCES users(id),
  uploaded_at         TIMESTAMP DEFAULT now(),
  updated_at          TIMESTAMP DEFAULT now()
);

-- ============================================================
-- TABLE 5: drawing_pages
-- One row per page of a multi-page P&ID
-- ============================================================
CREATE TABLE drawing_pages (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drawing_id        UUID NOT NULL REFERENCES pid_drawings(id) ON DELETE CASCADE,
  page_number       INTEGER NOT NULL,
  page_image_path   TEXT,                -- path to extracted PNG image of this page
  extraction_status VARCHAR(20) DEFAULT 'pending'
                    CHECK (extraction_status IN ('pending','processing','completed','failed')),
  extracted_at      TIMESTAMP,
  extraction_model  VARCHAR(100),        -- e.g. claude-opus-4-6, gpt-4o
  raw_llm_response  TEXT,               -- store the raw JSON from LLM for audit
  UNIQUE (drawing_id, page_number)
);

-- ============================================================
-- TABLE 6: equipment_tags
-- All equipment extracted from P&IDs (pumps, vessels, etc.)
-- ============================================================
CREATE TABLE equipment_tags (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id          UUID NOT NULL REFERENCES process_units(id),
  drawing_id       UUID NOT NULL REFERENCES pid_drawings(id),
  page_id          UUID NOT NULL REFERENCES drawing_pages(id),
  tag_number       VARCHAR(100) NOT NULL,   -- e.g. P-101A, E-201, V-301
  tag_type         VARCHAR(50),             -- PUMP, VESSEL, HEAT_EXCHANGER, COMPRESSOR, etc.
  description      TEXT,                    -- e.g. "Crude Charge Pump"
  service          TEXT,                    -- e.g. "Crude oil transfer"
  design_pressure  VARCHAR(50),
  design_temp      VARCHAR(50),
  capacity         VARCHAR(100),
  material         VARCHAR(100),
  notes            TEXT,
  created_at       TIMESTAMP DEFAULT now(),
  UNIQUE (unit_id, tag_number)
);

-- ============================================================
-- TABLE 7: instrument_tags
-- All instruments extracted from P&IDs
-- ============================================================
CREATE TABLE instrument_tags (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id           UUID NOT NULL REFERENCES process_units(id),
  drawing_id        UUID NOT NULL REFERENCES pid_drawings(id),
  page_id           UUID NOT NULL REFERENCES drawing_pages(id),
  tag_number        VARCHAR(100) NOT NULL,  -- e.g. FIC-1001, TT-2015, PV-3001
  instrument_type   VARCHAR(50),            -- FIC, TIC, PIC, LIC, XV, etc.
  description       TEXT,                   -- e.g. "Feed Flow Controller"
  process_variable  VARCHAR(50),            -- FLOW, TEMP, PRESSURE, LEVEL
  service           TEXT,
  range_low         VARCHAR(50),
  range_high        VARCHAR(50),
  unit_of_measure   VARCHAR(30),
  notes             TEXT,
  created_at        TIMESTAMP DEFAULT now(),
  UNIQUE (unit_id, tag_number)
);

-- ============================================================
-- TABLE 8: line_specs
-- All pipe lines extracted from P&IDs
-- ============================================================
CREATE TABLE line_specs (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id            UUID NOT NULL REFERENCES process_units(id),
  drawing_id         UUID NOT NULL REFERENCES pid_drawings(id),
  page_id            UUID NOT NULL REFERENCES drawing_pages(id),
  line_number        VARCHAR(100) NOT NULL,  -- e.g. 6"-HN-1001-150#-A1A
  nominal_diameter   VARCHAR(20),            -- e.g. 6"
  fluid_service      VARCHAR(50),            -- e.g. HN (Hot Naphtha)
  line_sequence      VARCHAR(20),            -- sequential number
  pressure_class     VARCHAR(20),            -- e.g. 150#, 300#, 600#
  pipe_spec          VARCHAR(20),            -- e.g. A1A, B2B
  insulation_code    VARCHAR(20),
  tracing_code       VARCHAR(20),
  from_equipment     VARCHAR(100),           -- upstream tag
  to_equipment       VARCHAR(100),           -- downstream tag
  notes              TEXT,
  created_at         TIMESTAMP DEFAULT now()
);

-- ============================================================
-- TABLE 9: tag_connectivity
-- Upstream/downstream relationships between tags
-- ============================================================
CREATE TABLE tag_connectivity (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id          UUID NOT NULL REFERENCES process_units(id),
  drawing_id       UUID NOT NULL REFERENCES pid_drawings(id),
  source_tag       VARCHAR(100) NOT NULL,  -- the tag we are connecting FROM
  source_tag_type  VARCHAR(20) NOT NULL    -- EQUIPMENT or INSTRUMENT or LINE
                   CHECK (source_tag_type IN ('EQUIPMENT','INSTRUMENT','LINE')),
  target_tag       VARCHAR(100) NOT NULL,  -- the tag this connects TO
  target_tag_type  VARCHAR(20) NOT NULL
                   CHECK (target_tag_type IN ('EQUIPMENT','INSTRUMENT','LINE')),
  direction        VARCHAR(20) NOT NULL    -- UPSTREAM or DOWNSTREAM
                   CHECK (direction IN ('UPSTREAM','DOWNSTREAM')),
  via_line         VARCHAR(100),           -- line number connecting them (optional)
  notes            TEXT,
  created_at       TIMESTAMP DEFAULT now()
);

-- ============================================================
-- TABLE 10: documents (operating manuals, SOPs)
-- ============================================================
CREATE TABLE documents (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id           UUID NOT NULL REFERENCES process_units(id),
  doc_type          VARCHAR(30) NOT NULL
                    CHECK (doc_type IN ('OPERATING_MANUAL','SOP','DATASHEET','OTHER')),
  doc_title         VARCHAR(300) NOT NULL,
  original_filename VARCHAR(300) NOT NULL,
  stored_filepath   TEXT NOT NULL,
  file_type         VARCHAR(10) NOT NULL,
  total_pages       INTEGER,
  processing_status VARCHAR(20) DEFAULT 'uploaded'
                    CHECK (processing_status IN ('uploaded','processing','indexed','failed')),
  uploaded_by       UUID REFERENCES users(id),
  uploaded_at       TIMESTAMP DEFAULT now()
);

-- ============================================================
-- TABLE 11: document_tag_references
-- Which tags are mentioned in which documents + context
-- ============================================================
CREATE TABLE document_tag_references (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  unit_id         UUID NOT NULL REFERENCES process_units(id),
  tag_number      VARCHAR(100) NOT NULL,
  page_number     INTEGER,
  section_title   VARCHAR(300),
  context_text    TEXT,           -- the paragraph or sentence mentioning this tag
  context_type    VARCHAR(50),    -- STARTUP, SHUTDOWN, NORMAL_OPERATION, EMERGENCY, etc.
  created_at      TIMESTAMP DEFAULT now()
);

-- ============================================================
-- TABLE 12: audit_logs
-- Every search, upload, and login action is recorded here
-- ============================================================
CREATE TABLE audit_logs (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID REFERENCES users(id),
  action       VARCHAR(100) NOT NULL,  -- UPLOAD_PID, SEARCH_TAG, LOGIN, etc.
  entity_type  VARCHAR(50),            -- DRAWING, TAG, DOCUMENT, USER
  entity_id    TEXT,                   -- the ID of the thing acted on
  details      JSONB,                  -- extra info as JSON
  ip_address   VARCHAR(45),
  created_at   TIMESTAMP DEFAULT now()
);

-- ============================================================
-- TABLE 13: llm_settings
-- Per-org LLM configuration (API key hint only — never store full key)
-- ============================================================
CREATE TABLE llm_settings (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        UUID NOT NULL REFERENCES organizations(id),
  provider      VARCHAR(30) NOT NULL
                CHECK (provider IN ('claude','openai','gemini')),
  model_name    VARCHAR(100) NOT NULL,  -- e.g. claude-opus-4-6, gpt-4o, gemini-1.5-pro
  api_key_hint  VARCHAR(20),            -- last 4 chars only, for display (NEVER store full key)
  is_active     BOOLEAN DEFAULT true,
  updated_by    UUID REFERENCES users(id),
  updated_at    TIMESTAMP DEFAULT now()
);

-- ============================================================
-- Auto-update triggers
-- Automatically sets updated_at = now() on every UPDATE
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER trg_drawings_updated_at
BEFORE UPDATE ON pid_drawings
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER trg_llm_settings_updated_at
BEFORE UPDATE ON llm_settings
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
