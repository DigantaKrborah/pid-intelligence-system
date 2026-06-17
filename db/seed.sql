-- ============================================================
-- P&ID Intelligence System — Seed Data
-- Organization: Numaligarh Refinery Ltd
--
-- Run this AFTER schema.sql has been applied.
-- All inserts use ON CONFLICT DO NOTHING so this script
-- is safe to run multiple times without creating duplicates.
-- ============================================================


-- ============================================================
-- 1. Organization
-- Fixed UUID so all other seed rows can reference it by ID
-- ============================================================
INSERT INTO organizations (id, org_name)
VALUES ('00000000-0000-0000-0000-000000000001', 'Numaligarh Refinery Ltd')
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 2. Admin user
-- Username: admin
-- Password: Admin@123  (stored as bcrypt hash below)
-- Change this password immediately after first login
-- ============================================================
INSERT INTO users (org_id, username, full_name, email, password_hash, role)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'admin',
  'System Administrator',
  'admin@nrl.co.in',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBP9Pq2WYZJ3VC',
  'admin'
)
ON CONFLICT (username) DO NOTHING;


-- ============================================================
-- 3. Process units — common NRL refinery units
-- Each row has a unique (org_id, unit_code) pair
-- ============================================================
INSERT INTO process_units (org_id, unit_code, unit_name, description) VALUES
  ('00000000-0000-0000-0000-000000000001', 'CDU',  'Crude Distillation Unit',       'Primary crude distillation'),
  ('00000000-0000-0000-0000-000000000001', 'VDU',  'Vacuum Distillation Unit',       'Vacuum distillation of reduced crude'),
  ('00000000-0000-0000-0000-000000000001', 'HCU',  'Hydrocracker Unit',              'Catalytic hydrocracking'),
  ('00000000-0000-0000-0000-000000000001', 'MSP',  'Motor Spirit Production Unit',   'Gasoline blending and production'),
  ('00000000-0000-0000-0000-000000000001', 'H2U',  'Hydrogen Generation Unit',       'Hydrogen production via SMR'),
  ('00000000-0000-0000-0000-000000000001', 'DHDT', 'Diesel Hydrotreater',            'Diesel desulphurization'),
  ('00000000-0000-0000-0000-000000000001', 'SRU',  'Sulphur Recovery Unit',          'Claus sulphur recovery'),
  ('00000000-0000-0000-0000-000000000001', 'CCR',  'Continuous Catalytic Reformer',  'Naphtha reforming'),
  ('00000000-0000-0000-0000-000000000001', 'UTIL', 'Utilities',                      'Steam, power, water, air utilities')
ON CONFLICT (org_id, unit_code) DO NOTHING;
