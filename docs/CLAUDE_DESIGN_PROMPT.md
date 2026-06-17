# Claude Design Prompt — P&ID Intelligence System
## Paste everything below this line into claude.ai/design

---

Design a complete **web application UI** for the **P&ID Intelligence System** — an AI-powered tool that transforms static P&ID (Piping & Instrumentation Diagram) PDF drawings into a searchable knowledge graph. Engineers at refineries and chemical plants upload P&ID sheets, then query equipment data using natural language.

---

## Product Context

**Users:** Process engineers, safety engineers, operations managers at oil refineries and chemical plants  
**Mental model:** Engineers are used to dark control-room interfaces. Think industrial SCADA + modern SaaS.  
**Framework:** Built in Streamlit — sidebar navigation, main content area, no persistent top nav bar  
**Key concept:** Everything is organised by **Process Unit** (CDU = Crude Distillation Unit, VDU = Vacuum Distillation Unit, HCU = Hydrocracking Unit, etc.). Users always work within a selected unit context.

---

## Design Language

### Colours
| Token | Hex | Usage |
|---|---|---|
| Background | `#0F1117` | Page background (Streamlit dark) |
| Surface | `#1E2130` | Cards, panels, sidebar |
| Surface raised | `#262B3D` | Hover states, selected rows |
| Border | `#2D3748` | Card borders, dividers |
| Primary | `#4F8EF7` | CTA buttons, links, active nav |
| Primary dim | `#1E3A6E` | Primary button hover bg |
| Success | `#22C55E` | Completed status, indexed badges |
| Warning | `#F59E0B` | Processing status, caution |
| Error | `#EF4444` | Failed status, critical alerts |
| Text primary | `#F1F5F9` | Headings, body |
| Text secondary | `#94A3B8` | Captions, metadata, placeholders |

### Equipment Type Colours (used in graph nodes, badges, and type pills)
| Equipment | Colour | Hex |
|---|---|---|
| Pump | Blue | `#3B82F6` |
| Vessel | Gray | `#6B7280` |
| Valve | Orange | `#F97316` |
| Instrument | Teal | `#14B8A6` |
| Exchanger | Green | `#22C55E` |
| Compressor | Purple | `#8B5CF6` |
| Line | Slate | `#CBD5E1` |

### Typography
- **Headings:** Inter Bold, 24px / 20px / 16px
- **Body:** Inter Regular, 14px
- **Equipment tags / codes:** `Roboto Mono` — all caps, e.g. `P-101`, `TIC-301`, `V-201`
- **Badges / pills:** Inter Medium, 11px

### Components
- **Cards:** `#1E2130` background, `1px solid #2D3748` border, `8px` radius, subtle `box-shadow: 0 2px 8px rgba(0,0,0,0.4)` on hover
- **Primary button:** `#4F8EF7` fill, white text, `6px` radius
- **Secondary button:** transparent, `#4F8EF7` border and text
- **Input fields:** `#262B3D` background, `#2D3748` border, `#F1F5F9` text
- **Status badges (pill shape):** coloured background at 15% opacity, matching coloured text
  - Queued: gray · Processing: blue with spinner · Completed: green · Failed: red
- **Type badges:** equipment colour at 20% opacity background, full-colour text

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  Sidebar (260px fixed)  │  Main Content (flexible)       │
│                         │                                │
│  ⚙️ P&ID Intel          │  Page header                   │
│  🟢 API Online          │                                │
│  ────────────────       │  Page content                  │
│  [CDU ▾] Unit selector  │                                │
│  [+ New Unit]           │                                │
│  ────────────────       │                                │
│  📤 Upload P&IDs        │                                │
│  🔍 Search Tags         │                                │
│  🕸️ Process Graph      │                                │
│  💬 Ask a Question      │                                │
│  📄 Documents           │                                │
│  🚨 Incidents           │                                │
│  ────────────────       │                                │
│  🐛 Report Bug          │                                │
└─────────────────────────────────────────────────────────┘
```

Sidebar always visible. Active nav item has `#4F8EF7` left border + slightly lighter background.

---

## Screens to Design (8 screens)

---

### Screen 1 — Home Dashboard (unit selected: CDU)

**Sidebar state:** CDU selected in unit dropdown, "Dashboard" nav item active

**Main content:**
- Page header: `⚙️ CDU` (large), caption `Crude Distillation Unit`
- **Stats row** — 4 metric cards side by side:
  - `247` Equipment Tags
  - `18` P&ID Sheets  
  - `5` SOPs Indexed
  - `12` Graph Nodes
- **Quick Actions row** — 3 equal-width buttons: `📤 Upload P&IDs` · `🔍 Search Tags` · `💬 Ask a Question`
- **Two-column layout below:**
  - **Left (2/3):** "Recent Uploads" section — table with columns: Filename, Pages, Tags, Status badge, Uploaded date. Show 3 rows: one Completed (green), one Processing (blue spinner), one Failed (red).
  - **Right (1/3):** Graph summary card — metrics for Nodes and Edges, `🕸️ View Graph` button

---

### Screen 2 — Unit Management (no unit selected — welcome state)

**Sidebar state:** "— Select Unit —" in dropdown

**Main content:**
- Welcome header: `Welcome to P&ID Intelligence System`
- Info banner: "👈 Select a process unit from the sidebar to get started."
- **Global stats row:** Total Units `4`, Total Tags `891`, P&ID Sheets `67`
- **Units grid** — 4 unit cards in a 2×2 grid:
  - Each card: unit name (bold, large), description, `Tags: 247`, `Sheets: 18`, `[Open]` button, status badge `Active`
  - Units shown: CDU, VDU, HCU, FCC

**Create Unit modal** (shown overlaid — semi-transparent backdrop):
- Title: "Create New Process Unit"
- `Unit Name *` text input (value: "HCU")
- `Description` textarea
- Two buttons: `✅ Create` (primary) · `Cancel` (secondary)

---

### Screen 3 — P&ID Upload

**Sidebar state:** CDU selected, "Upload P&IDs" nav item active

**Main content:**
- Breadcrumb: `CDU / Upload P&IDs`
- **File selection table** (files already selected, pre-upload):
  - Header row: Filename | Size | Status
  - Row 1: `P&ID-CDU-001.pdf` | 4.2 MB | ✅ Ready
  - Row 2: `P&ID-CDU-002.pdf` | 6.8 MB | ✅ Ready
  - Row 3: `P&ID-CDU-003.pdf` | 51.0 MB | ⚠️ Too large
- `🚀 Upload & Process` primary button (large)
- **Below (after upload starts) — Processing status section:**
  - `P&ID-CDU-001.pdf` — 🟢 **Done** — 42 tags from 8 pages
  - `P&ID-CDU-002.pdf` — 🔵 **Extracting tags...** (blue spinner)
  - `P&ID-CDU-003.pdf` — ⏳ Queued

---

### Screen 4 — Equipment Search

**Sidebar state:** CDU selected, "Search Tags" active

**Main content — two columns:**

**Left column (40%) — Search + Results:**
- Full-width search bar: `P-101` (typed), with `🔍` icon
- Filter row: `Unit: CDU ▾` | `Type: All Types ▾` | `Semantic search` toggle (off)
- Caption: `4 result(s)`
- Result cards (3 visible):
  - Card 1 (selected/highlighted): **`P-101`** 💧 `pump` · CDU | "Feed pump" | `[View details]` button
  - Card 2: **`P-102`** 💧 `pump` · CDU | "Reflux pump"
  - Card 3: **`P-103`** 💧 `pump` · CDU | "Bottoms pump"

**Right column (60%) — Detail panel (P-101 selected):**
- Header: `⚙️ P-101` large, caption `Centrifugal Pump · CDU`
- Description: "Feed pump — transfers crude from storage to preheat train"
- **Connected equipment section:**
  - ⬆️ Upstream: `V-101` chip · `FCV-101` chip
  - ⬇️ Downstream: `E-101` chip · `E-102` chip
- Source: "page 3"
- Action buttons row: `🕸️ View in Graph` · `💬 Ask about this`
- **Impact Analysis expander** (open): 
  - Severity: 🟡 Medium
  - Metric: "3 affected equipment"
  - Pumps: `P-201` | Vessels: `V-201` | Exchangers: `E-301`

---

### Screen 5 — Process Graph Visualisation *(hero screen — make this the most impressive)*

**Sidebar state:** CDU selected, "Process Graph" active

**Top controls bar (full width):**
`Highlight tag: [P-101]` input | `Cross-unit` toggle (on) | `Physics` toggle (on) | `Node size` slider

**Main area — two columns:**

**Left (3/4) — Graph canvas:**
- Dark canvas (`#0A0E1A` background — even darker than page bg)
- Rich node-link graph with ~25 nodes:
  - Blue circles: P-101, P-102, P-103, P-201 (pumps)
  - Gray hexagons: V-101, V-201, T-101 (vessels/columns — larger)
  - Orange diamonds: FCV-101, FCV-102, LV-101, PCV-101 (valves)
  - Teal squares: TIC-301, FIC-101, LIC-201, PIC-101 (instruments — small)
  - Green rectangles: E-101, E-102, E-201 (exchangers)
  - Purple circles: C-101 (compressor)
- **P-101 node:** larger, bright white glow ring, selected state
- **Edges:** solid light gray lines between most nodes; 2 dashed lines to cross-unit nodes
- **Two cross-unit nodes** (dotted white border): `V-301-VDU` · `P-401-VDU` in a different cluster, connected by dashed orange lines
- Subtle grid/dot pattern background texture
- Physics simulation gives organic layout — not a grid

**Right (1/4) — Node detail panel (P-101):**
- `⚙️ P-101` heading
- Upstream section: `V-101` button · `FCV-101` button
- Downstream section: `E-101` button · `E-102` button
- Divider
- Impact section: 🟡 Medium · "3 affected downstream"
- Divider  
- `💬 Ask about this tag` button (full width)

**Bottom stats bar:** Nodes: `24` · Edges: `31` · "Click a node to inspect it"

---

### Screen 6 — Natural Language Chat

**Sidebar state:** CDU selected, "Ask a Question" active

**Top context bar:** `Querying unit: **CDU**`

**Chat area (scrollable, 3 turns shown):**

*Turn 1:*
- User bubble (right, blue `#4F8EF7`): "List all pumps in the CDU unit"
- AI card (left, `#1E2130` surface): 
  - Text: "There are **4 centrifugal pumps** in the CDU unit:"
  - Data table: Tag | Type | Description | Status rows: P-101 Feed pump / P-102 Reflux pump / P-103 Bottoms pump / P-201 Overhead pump
  - Sources expander (collapsed): "📄 P&ID-CDU-001.pdf — page 3"

*Turn 2:*
- User bubble: "What is downstream of V-101?"
- AI card:
  - Text: "Downstream of **V-101** (Feed Drum):"
  - Tag chips in a row: `P-101` · `FCV-101` · `E-101`
  - Sources expander (collapsed)

*Turn 3 (latest):*
- User bubble: "What happens if P-101 fails?"
- AI card:
  - Text: "If **P-101** is isolated or fails, the following downstream equipment is affected:"
  - Severity badge: 🟡 **Medium Impact — 3 equipment affected**
  - Three impact rows with type icons
  - Sources (open): "📄 P&ID-CDU-001.pdf — page 3"

**Bottom input (sticky):**
- Text field: placeholder "Ask about CDU equipment, process paths, or SOPs..."
- `Send` button (blue)
- `🗑️ Clear chat` link (right-aligned)

---

### Screen 7 — Documents (SOPs & Manuals)

**Sidebar state:** CDU selected, "Documents" active

**Upload expander (collapsed):** "📤 Upload a Document ▸"

**Search bar:** `🔍 Search documents` — `startup procedure` typed

**Search results section** (3 results, from semantic search):
- Result 1: **CDU_Startup_SOP.pdf** · page 12 · CDU — "Open isolation valve V-101 before starting feed pump P-101. Verify pressure readings on PIC-101..."
- Result 2: **CDU_Startup_SOP.pdf** · page 14 · CDU — "Start P-101 at minimum speed. Monitor FIC-101 flow rate target 450 m³/h..."
- Result 3: **CDU_Operations_Manual.pdf** · page 8 · CDU — "Normal operating procedure: pre-heat train temperature TIC-301 target 280°C..."

**Indexed Documents table:**
Header: Filename | Type | Pages | Chunks | Indexed
Rows:
- CDU_Startup_SOP.pdf | SOP | 28 | 47 | ✅
- CDU_Operations_Manual.pdf | Manual | 156 | 312 | ✅
- CDU_Equipment_Datasheet.pdf | Datasheet | 12 | — | ⏳ (indexing)

---

### Screen 8 — Incidents

**Sidebar state:** CDU selected, "Incidents" active

**Report New Incident expander (open):**
- Title input: "P-101 mechanical seal leak"
- Description textarea: "Feed pump developing visible leak from mechanical seal..."
- Severity: `high` selected
- Related Tags: `P-101, FCV-101`
- `Report Incident` primary button

**Filter row:** Status filter: `All ▾` | `☐ Show all units`

**Incidents list (3 incidents):**

Incident 1:
- 🟠 **P-101 mechanical seal leak** · 🔓 Open
- "Feed pump developing visible leak..." 
- Tags: `P-101` `FCV-101`
- Reported: 2026-06-04 | `[Resolve]` button

Incident 2 (in resolve mode — inline form shown):
- 🟡 **TIC-301 reading drift** · 🔎 Investigating  
- Resolution notes textarea: "Calibration scheduled..."
- `Confirm Resolve` button · `Cancel` button

Incident 3:
- 🟢 **V-101 level gauge replacement** · ✅ Resolved
- Tags: `V-101` `LIC-201`
- Reported: 2026-05-28 · Resolved: 2026-06-01

---

## Key Interaction States to Show

Show these specific states within the 8 screens above:

1. **Sidebar dropdown** — expanded with: CDU · VDU · HCU · FCC · `+ New Unit`
2. **Upload processing** — one file at "Extracting tags..." state with blue spinner badge
3. **Graph selected node** — P-101 glowing with right panel showing upstream/downstream
4. **Chat AI response** — multi-turn conversation with table, chips, and open sources section
5. **Search detail panel** — P-101 selected showing connections + impact analysis
6. **Incident resolve flow** — inline resolution form expanded on an incident card

---

## Realism Requirements

Use these realistic P&ID tag names throughout (not generic "Tag 1"):
- **Pumps:** P-101, P-102, P-103, P-201, P-202
- **Vessels/Columns:** V-101, V-201, T-101 (main column), T-102
- **Control valves:** FCV-101, LV-101, PCV-101, FCV-201
- **Instruments:** TIC-301, FIC-101, LIC-201, PIC-101, FT-101
- **Exchangers:** E-101, E-102, E-201, E-301
- **Units:** CDU (Crude Distillation), VDU (Vacuum Distillation), HCU (Hydrocracking), FCC (Fluid Catalytic Cracking)

Use realistic file names: `P&ID-CDU-001.pdf`, `P&ID-CDU-002.pdf`, `CDU_Startup_SOP.pdf`, `CDU_Operations_Manual.pdf`

Use realistic numbers: 247 tags, 18 sheets, 5 SOPs, 24 graph nodes

---

## Final Note

Design all 8 screens with a **consistent, professional design language**. The product should feel like a **serious engineering tool used in an industrial control room** — not a startup dashboard. The graph visualisation (Screen 5) should be the centrepiece: visually rich, technically impressive, and immediately communicating the value of having a P&ID knowledge graph. Every screen should make an experienced process engineer think "this understands my job."
