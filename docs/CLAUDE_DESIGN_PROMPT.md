# Claude Design Prompt
## Copy everything between the lines and paste into Claude Design (claude.ai/design)

---

Design a **web application UI** for the **P&ID Intelligence System** — an AI-powered tool that helps process engineers at refineries and chemical plants search, query, and visualise their Piping & Instrumentation Diagrams (P&IDs).

---

### Design Brief

**Product:** P&ID Intelligence System
**Users:** Process engineers, safety engineers, operations managers at refineries
**Vibe:** Professional, technical, industrial. Think control-room dashboard meets modern SaaS. Dark or deep-blue theme preferred (engineers work in dark control rooms). Clean, data-dense, not playful.
**Framework:** Streamlit (so standard web UI patterns — sidebar navigation, main content, modals)

---

### Screens to Design (7 screens)

#### Screen 1 — Home Dashboard
- **Left sidebar:** App logo ("P&ID Intel"), nav links (Dashboard, Upload, Search, Graph, Chat, Documents), unit selector dropdown at top of sidebar (shows "CDU ▾", list of user units, "+ New Unit" option)
- **Main area:** 
  - Header: "CDU — Crude Distillation Unit" + "Last updated: 2 hours ago" badge
  - **Stats row:** 4 metric cards — Total Tags (247), P&ID Sheets (18), SOPs Indexed (5), Processing Queue (0)
  - **Recent Activity table:** columns — Filename, Pages, Tags Extracted, Status (green "Completed" / orange "Processing" / red "Failed"), Uploaded
  - **Quick Actions:** 3 buttons — "Upload P&IDs", "Search Tags", "Ask a Question"

#### Screen 2 — Unit Management / Create New Unit
- Modal overlay or dedicated page
- Form: Unit Name (text input, placeholder "e.g. CDU, VDU, HCU"), Description (textarea), Unit Code (auto-suggested)
- Below form: existing units list as cards — each card shows unit name, tag count, document count, last activity, status badge (Active/Archived), action buttons (Open, Archive)

#### Screen 3 — P&ID Upload
- **Unit selector** at top (breadcrumb: "CDU > Upload P&IDs")
- **Drag-and-drop upload zone** (large, dashed border): "Drop P&ID PDF files here or click to browse" with file type and size hints (PDF, max 50MB per file, max 50 files)
- **Upload queue table** below: columns — Filename, Size, Pages, Status with progress bar, Actions
- Status badges: Queued (gray), Processing (blue spinner), Extracting Tags (blue), Building Graph (purple), Completed (green), Failed (red with retry button)
- **Processing summary** card on right: showing "Pages Processed: 12/48", "Tags Found: 156", "Estimated Time: 4 min"

#### Screen 4 — Equipment Search
- **Search bar** (prominent, full width): "Search equipment tags, e.g. P-101, TIC-301, V-201..."
- **Filter chips** below: All Types | Pumps | Vessels | Valves | Instruments | Exchangers | Heat Exchangers
- **Unit filter** pills: All Units | CDU | VDU | HCU
- **Results list** (left 60%):
  - Each result is a card: Tag (bold, large, e.g. "P-101"), Type badge (green "Centrifugal Pump"), Unit badge (blue "CDU"), Description, Source sheet (clickable "Sheet 3 - P&ID-CDU-003.pdf")
- **Detail panel** (right 40%) on click:
  - Tag header with type icon
  - Attributes table
  - **Connected Equipment** list (upstream/downstream neighbours as clickable chips)
  - "View in Graph" button
  - "Ask about this tag" button → opens chat with pre-filled context

#### Screen 5 — Process Graph Visualisation
- **Controls bar** (top): Unit selector, View toggle (Single Unit / Cross-Unit), Layout selector (Force-directed / Hierarchical), Search node input, Zoom controls
- **Main graph canvas** (full remaining area): 
  - Node colours by type: pumps=blue circles, vessels=large gray hexagons, valves=orange diamonds, instruments=small teal squares, exchangers=green rectangles
  - Edges: solid lines for process flow, dashed for signal/utility
  - Selected node highlighted with glow effect
  - Cross-unit nodes shown with dotted border
- **Node detail sidebar** (right, appears on click): tag name, type, unit, attributes, upstream/downstream list, "Find path to..." button

#### Screen 6 — Natural Language Chat (AI Query)
- **Unit context bar** at top: "Querying: CDU — Crude Distillation Unit" + "Switch Unit" link
- **Chat area** (main, scrollable):
  - User messages: right-aligned, blue bubble
  - AI responses: left-aligned, dark card with:
    - Answer text
    - Supporting data (table or equipment tag chips)
    - "Sources" expandable section (which P&ID sheet, which SOP)
    - Confidence badge
  - **Example queries panel** (shown when chat is empty): 4–6 suggestion chips e.g. "List all pumps in CDU", "What is downstream of V-101?", "Which instruments monitor reactor pressure?"
- **Input area** (bottom, sticky): text field + Send button + "Clear Chat" link

#### Screen 7 — Documents (SOP / Manual Management)
- **Upload area** (top): compact drag-and-drop for PDF/DOCX, assign to unit dropdown
- **Documents table**: Filename, Unit, Type (SOP/Manual/Datasheet), Pages, Indexed (yes/no badge), Upload Date, Actions (View, Re-index, Delete)
- **Search documents** bar above table: semantic search across all indexed docs

---

### Design Tokens / Style Guide

**Colours:**
- Background: `#0F1117` (very dark navy, like Streamlit dark theme)
- Surface/Card: `#1E2130`
- Primary accent: `#4F8EF7` (engineering blue)
- Success: `#22C55E`
- Warning: `#F59E0B`
- Error/Critical: `#EF4444`
- Text primary: `#F1F5F9`
- Text secondary: `#94A3B8`

**Equipment type colours (for graph nodes and badges):**
- Pump: `#3B82F6` (blue)
- Vessel: `#6B7280` (gray)
- Valve: `#F97316` (orange)
- Instrument: `#14B8A6` (teal)
- Exchanger: `#22C55E` (green)
- Compressor: `#8B5CF6` (purple)

**Typography:**
- Headings: Inter or Roboto, bold
- Body: Inter, regular
- Tags/codes: Roboto Mono (monospace for equipment tag IDs like P-101)

**Component style:**
- Cards: subtle border `#2D3748`, 8px radius, slight hover lift shadow
- Badges: pill shape, coloured background matching type colour at 20% opacity, coloured text
- Buttons: primary = filled blue, secondary = outlined

---

### Key Interactions to Show

1. **Sidebar unit selector** — show dropdown expanded with 4 units + "+ New Unit"
2. **Upload progress** — show one file at "Building Graph" stage with purple badge
3. **Graph node selected** — show detail sidebar open with upstream/downstream connections
4. **Chat response** — show a multi-part answer with a data table and sources section
5. **Search results** — show 3 results with the right-panel detail view open

---

### Layout Notes

- Sidebar: 260px fixed left
- Content area: responsive, 12-column grid
- Responsive breakpoint: works at 1280px minimum (engineers use large monitors)
- No mobile layout needed

---

Design all 7 screens with consistent design language. Make it feel like a serious, professional engineering tool — not a toy. The graph visualisation screen should feel the most impressive as it's the centrepiece of the product.
