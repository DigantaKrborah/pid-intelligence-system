"""
Design system for P&ID Intelligence System.
Call inject_css() at the top of every page.
All HTML helpers return strings — pass to st.markdown(..., unsafe_allow_html=True).
"""

# ── Design tokens ──────────────────────────────────────────────────────────────
COLOURS = {
    "bg":        "#0F1117",
    "surface":   "#1E2130",
    "surface2":  "#262B3D",
    "border":    "#2D3748",
    "primary":   "#4F8EF7",
    "success":   "#22C55E",
    "warning":   "#F59E0B",
    "error":     "#EF4444",
    "txt":       "#F1F5F9",
    "txt2":      "#94A3B8",
}

TYPE_COLOURS = {
    "pump":       "#3B82F6",
    "vessel":     "#6B7280",
    "valve":      "#F97316",
    "instrument": "#14B8A6",
    "exchanger":  "#22C55E",
    "compressor": "#8B5CF6",
    "line":       "#CBD5E1",
    "other":      "#94A3B8",
}

SEVERITY_COLOURS = {
    "critical": "#EF4444",
    "high":     "#F97316",
    "medium":   "#F59E0B",
    "low":      "#22C55E",
}

# ── Global CSS ─────────────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&display=swap');

:root {
  --bg:#0F1117; --surface:#1E2130; --surface2:#262B3D; --border:#2D3748;
  --primary:#4F8EF7; --success:#22C55E; --warning:#F59E0B; --error:#EF4444;
  --txt:#F1F5F9; --txt2:#94A3B8;
}

/* ── Metric cards ── */
[data-testid="metric-container"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  padding: 14px 16px !important;
  transition: box-shadow .15s;
}
[data-testid="metric-container"]:hover {
  box-shadow: 0 2px 10px rgba(0,0,0,.5) !important;
}
[data-testid="stMetricValue"] > div {
  font-size: 26px !important;
  font-weight: 700 !important;
  color: var(--txt) !important;
}
[data-testid="stMetricLabel"] {
  font-size: 11px !important;
  font-weight: 600 !important;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--txt2) !important;
}

/* ── Bordered containers ── */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  padding: 4px !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color: #3d4e66 !important;
}

/* ── Buttons ── */
.stButton > button {
  border-radius: 6px !important;
  font-weight: 500 !important;
  transition: all .15s !important;
  font-size: 13px !important;
}
.stButton > button[kind="primary"] {
  background: var(--primary) !important;
  border: none !important;
  color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
  background: #3b7ce8 !important;
  box-shadow: 0 2px 8px rgba(79,142,247,.35) !important;
}
.stButton > button[kind="secondary"] {
  background: transparent !important;
  border: 1px solid var(--primary) !important;
  color: var(--primary) !important;
}
.stButton > button[kind="secondary"]:hover {
  background: rgba(79,142,247,.08) !important;
}
.stFormSubmitButton > button {
  border-radius: 6px !important;
  font-weight: 500 !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
  color: var(--txt) !important;
  font-size: 13px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 1px var(--primary) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploaderDropzone"] {
  background: var(--surface2) !important;
  border: 2px dashed var(--border) !important;
  border-radius: 8px !important;
  transition: border-color .15s !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--primary) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  overflow: hidden !important;
}
[data-testid="stExpander"] summary {
  font-size: 13px !important;
  font-weight: 600 !important;
  padding: 10px 14px !important;
}
[data-testid="stExpander"] summary:hover {
  background: var(--surface2) !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessageContent"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  font-size: 13px !important;
  line-height: 1.6 !important;
}
/* User message — right align and blue */
[data-testid="stChatMessageContainer"][data-testid*="user-message"] > div:last-child {
  background: var(--primary) !important;
  border-color: var(--primary) !important;
}

/* ── Dividers ── */
hr { border-color: var(--border) !important; opacity: 1 !important; }

/* ── Code / monospace tags ── */
code {
  font-family: 'Roboto Mono', 'Courier New', monospace !important;
  background: rgba(79,142,247,.12) !important;
  color: #7eb8ff !important;
  padding: 2px 6px !important;
  border-radius: 4px !important;
  font-size: 12px !important;
}

/* ── Headings ── */
h1 { font-weight: 700 !important; letter-spacing: -.01em; color: #F1F5F9 !important; }
h2 { font-weight: 600 !important; color: #F1F5F9 !important; }
h3 { font-weight: 600 !important; color: #F1F5F9 !important; }
[data-testid="stCaptionContainer"] p { color: var(--txt2) !important; }

/* ── Force all text inside markdown/html blocks to be visible ── */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] div,
[data-testid="stMarkdownContainer"] td,
[data-testid="stMarkdownContainer"] th {
  color: #F1F5F9 !important;
}
/* Custom HTML blocks rendered via unsafe_allow_html */
.stMarkdown div, .stMarkdown p, .stMarkdown span {
  color: #F1F5F9;
}
/* Catch-all for any injected HTML divs that inherit browser default (black) */
[data-testid="stHtml"] *, .element-container div {
  color: #F1F5F9;
}

/* ── Chat message text ── */
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] span,
[data-testid="stChatMessageContent"] div {
  color: #F1F5F9 !important;
}

/* ── Alert boxes ── */
[data-testid="stAlertContainer"] { border-radius: 8px !important; }
[data-testid="stAlertContainer"] p { color: inherit !important; }

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div {
  background: var(--primary) !important;
  border-radius: 4px !important;
}

/* ── Toggle ── */
[data-testid="stCheckbox"] span[data-testid="stWidgetLabel"] { font-size: 13px; }

/* ── Sidebar health status ── */
.pid-health { font-size: 11px; padding: 0 0 8px 0; }

/* ── Custom component resets ── */
.pid-card { margin-bottom: 8px; }
</style>
"""


def inject_css() -> None:
    """Call once at the top of every page."""
    import streamlit as st
    st.markdown(_CSS, unsafe_allow_html=True)


# ── Badge components ───────────────────────────────────────────────────────────

def status_badge(status: str) -> str:
    """Colored processing-status pill."""
    cfg = {
        "pending":        ("⏳", "#64748B", "rgba(100,116,139,.15)"),
        "queued":         ("⏳", "#94A3B8", "rgba(148,163,184,.12)"),
        "processing":     ("◌", "#4F8EF7", "rgba(79,142,247,.15)"),
        "extracting":     ("◌", "#4F8EF7", "rgba(79,142,247,.15)"),
        "building_graph": ("◌", "#8B5CF6", "rgba(139,92,246,.15)"),
        "completed":      ("✓", "#22C55E", "rgba(34,197,94,.15)"),
        "failed":         ("✕", "#EF4444", "rgba(239,68,68,.15)"),
        "indexed":        ("✓", "#22C55E", "rgba(34,197,94,.15)"),
        "active":         ("●", "#22C55E", "rgba(34,197,94,.15)"),
        "archived":       ("○", "#94A3B8", "rgba(148,163,184,.12)"),
        "open":           ("🔓", "#F59E0B", "rgba(245,158,11,.15)"),
        "investigating":  ("🔎", "#4F8EF7", "rgba(79,142,247,.15)"),
        "resolved":       ("✓", "#22C55E", "rgba(34,197,94,.15)"),
    }
    icon, color, bg = cfg.get(status.lower(), ("·", "#94A3B8", "rgba(148,163,184,.12)"))
    label = {
        "processing":     "Processing…",
        "extracting":     "Extracting tags…",
        "building_graph": "Building graph…",
        "completed":      "Completed",
        "failed":         "Failed",
        "indexed":        "Indexed",
    }.get(status.lower(), status.replace("_", " ").title())
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 9px;'
        f'border-radius:20px;font-size:11px;font-weight:600;background:{bg};color:{color}">'
        f'{icon} {label}</span>'
    )


def type_badge(tag_type: str) -> str:
    """Colored equipment-type pill."""
    color = TYPE_COLOURS.get(tag_type.lower(), "#94A3B8")
    r, g, b = _hex_to_rgb(color)
    return (
        f'<span style="display:inline-flex;align-items:center;padding:2px 8px;'
        f'border-radius:20px;font-size:11px;font-weight:600;'
        f'background:rgba({r},{g},{b},.18);color:{color}">'
        f'{tag_type}</span>'
    )


def severity_badge(severity: str) -> str:
    """Colored severity pill for incidents."""
    icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    color = SEVERITY_COLOURS.get(severity.lower(), "#94A3B8")
    r, g, b = _hex_to_rgb(color)
    icon = icons.get(severity.lower(), "⚪")
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 9px;'
        f'border-radius:20px;font-size:11px;font-weight:600;'
        f'background:rgba({r},{g},{b},.15);color:{color}">'
        f'{icon} {severity.title()}</span>'
    )


def tag_chip(tag: str, color: str | None = None) -> str:
    """Monospace equipment tag chip."""
    c = color or "#4F8EF7"
    r, g, b = _hex_to_rgb(c)
    return (
        f'<code style="font-family:\'Roboto Mono\',monospace;font-size:12px;'
        f'background:rgba({r},{g},{b},.12);color:{c};padding:3px 8px;'
        f'border-radius:5px;border:1px solid rgba({r},{g},{b},.25);'
        f'display:inline-block;margin:2px">{tag}</code>'
    )


def tag_chips_row(tags: list[str], tag_type: str = "other") -> str:
    """Row of tag chips coloured by type."""
    color = TYPE_COLOURS.get(tag_type.lower(), "#4F8EF7")
    return "".join(tag_chip(t, color) for t in tags)


# ── Card components ────────────────────────────────────────────────────────────

def section_title(title: str) -> str:
    return (
        f'<div style="font-size:11px;font-weight:700;color:#64748B;'
        f'text-transform:uppercase;letter-spacing:.07em;margin:16px 0 8px">'
        f'{title}</div>'
    )


def result_card(tag: str, tag_type: str, unit_name: str,
                description: str, score: float, selected: bool = False) -> str:
    border = "#4F8EF7" if selected else "#2D3748"
    color = TYPE_COLOURS.get(tag_type.lower(), "#94A3B8")
    r, g, b = _hex_to_rgb(color)
    return f"""
<div style="background:#1E2130;border:1px solid {border};border-radius:8px;
  padding:12px 14px;margin-bottom:8px;transition:border-color .12s;cursor:pointer;color:#F1F5F9">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
    <code style="font-family:'Roboto Mono',monospace;font-size:15px;font-weight:700;
      color:#F1F5F9;background:transparent;padding:0;border:none">{tag}</code>
    <span style="display:inline-flex;align-items:center;padding:2px 7px;border-radius:20px;
      font-size:10px;font-weight:600;background:rgba({r},{g},{b},.18);color:{color}">{tag_type}</span>
    <span style="display:inline-flex;align-items:center;padding:2px 7px;border-radius:20px;
      font-size:10px;font-weight:600;background:rgba(79,142,247,.15);color:#4F8EF7">{unit_name}</span>
  </div>
  <div style="font-size:12px;color:#94A3B8;margin-bottom:0">{description or ""}</div>
</div>"""


def processing_row(filename: str, status: str, tags: int = 0, pages: str = "?") -> str:
    badge = status_badge(status)
    extra = ""
    if status == "completed":
        extra = f'<span style="font-size:11px;color:#94A3B8;margin-left:8px">{tags} tags · {pages} pages</span>'
    elif status == "failed":
        extra = '<span style="font-size:11px;color:#EF4444;margin-left:8px">see logs</span>'
    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;
  padding:10px 14px;background:#1E2130;border-bottom:1px solid #2D3748">
  <code style="font-family:'Roboto Mono',monospace;font-size:12px;color:#F1F5F9;
    background:transparent;padding:0;border:none">{filename}</code>
  <div style="display:flex;align-items:center;gap:6px">{badge}{extra}</div>
</div>"""


def upload_file_row(filename: str, size_mb: float, valid: bool) -> str:
    if valid:
        status_html = '<span style="color:#22C55E;font-size:12px;font-weight:600">✅ Ready</span>'
    else:
        status_html = '<span style="color:#F59E0B;font-size:12px;font-weight:600">⚠️ Too large</span>'
    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;
  padding:9px 14px;background:#1E2130;border-bottom:1px solid #2D3748">
  <code style="font-family:'Roboto Mono',monospace;font-size:12px;color:#F1F5F9;
    background:transparent;padding:0;border:none">{filename}</code>
  <span style="font-size:12px;color:#94A3B8;min-width:60px;text-align:right">{size_mb:.1f} MB</span>
  <div style="min-width:90px;text-align:right">{status_html}</div>
</div>"""


def impact_panel(severity: str, count: int, by_type: dict) -> str:
    sev_badge = severity_badge(severity)
    rows = ""
    for typ, tags in by_type.items():
        color = TYPE_COLOURS.get(typ, "#94A3B8")
        chips = "".join(tag_chip(t, color) for t in tags[:8])
        rows += f'<div style="margin-bottom:6px"><span style="font-size:11px;color:{color};font-weight:600;text-transform:capitalize">{typ}s:</span><br>{chips}</div>'
    return f"""
<div style="background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.2);
  border-radius:8px;padding:12px 14px;color:#F1F5F9">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
    {sev_badge}
    <span style="font-size:12px;color:#94A3B8">{count} equipment affected</span>
  </div>
  {rows}
</div>"""


def chat_user_bubble(content: str) -> str:
    return f"""
<div style="display:flex;justify-content:flex-end;margin:8px 0 12px">
  <div style="background:#4F8EF7;color:#fff;padding:10px 14px;
    border-radius:14px 14px 3px 14px;max-width:72%;font-size:13px;line-height:1.6;
    box-shadow:0 2px 6px rgba(79,142,247,.3)">{content}</div>
</div>"""


def chat_ai_card(answer: str, sources: list | None = None) -> str:
    sources_html = ""
    if sources:
        items = "".join(
            f'<div style="padding:3px 0;font-size:11px;color:#94A3B8">'
            f'📄 {s.get("source","?")} — page {s.get("page","?")}</div>'
            for s in sources
        )
        sources_html = f"""
<details style="margin-top:10px">
  <summary style="font-size:11px;color:#94A3B8;cursor:pointer;user-select:none">
    📄 Sources ({len(sources)})</summary>
  <div style="background:#262B3D;border-radius:6px;padding:8px 10px;margin-top:6px;color:#94A3B8">
    {items}
  </div>
</details>"""
    return f"""
<div style="display:flex;justify-content:flex-start;margin:8px 0 12px">
  <div style="background:#1E2130;border:1px solid #2D3748;padding:14px 16px;
    border-radius:3px 14px 14px 14px;max-width:88%;font-size:13px;line-height:1.6;
    color:#F1F5F9">
    {answer}{sources_html}
  </div>
</div>"""


def incident_card(inc: dict) -> str:
    severity  = inc.get("severity", "medium")
    status    = inc.get("status", "open")
    sev_badge = severity_badge(severity)
    stat_badge = status_badge(status)
    tags = inc.get("related_tags") or []
    chips = "".join(tag_chip(t) for t in tags[:6])
    resolved_line = ""
    if status == "resolved" and inc.get("resolved_at"):
        resolved_line = f'<span style="font-size:11px;color:#22C55E">Resolved: {str(inc["resolved_at"])[:10]}</span>'
    opacity = "opacity:.8;" if status == "resolved" else ""
    return f"""
<div style="background:#1E2130;border:1px solid #2D3748;border-radius:8px;
  padding:14px 16px;margin-bottom:10px;{opacity}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
    <div style="font-weight:600;font-size:14px;color:#F1F5F9">{inc.get("title","")}</div>
    <div style="display:flex;gap:6px;align-items:center;flex-shrink:0;margin-left:12px">
      {sev_badge}{stat_badge}
    </div>
  </div>
  <div style="font-size:12px;color:#94A3B8;margin-bottom:8px">{(inc.get("description") or "")[:160]}</div>
  <div style="margin-bottom:6px">{chips}</div>
  <div style="font-size:11px;color:#64748B">Reported: {str(inc.get("reported_at",""))[:10]} {resolved_line}</div>
</div>"""


def doc_row(doc: dict) -> str:
    indexed = doc.get("indexed", False)
    ind_badge = status_badge("indexed") if indexed else status_badge("processing")
    dtype = doc.get("doc_type") or "—"
    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;
  padding:10px 14px;background:#1E2130;border-bottom:1px solid #2D3748">
  <code style="font-family:'Roboto Mono',monospace;font-size:12px;color:#F1F5F9;
    background:transparent;padding:0;border:none;max-width:260px;overflow:hidden;
    text-overflow:ellipsis;white-space:nowrap">{doc.get("filename","")}</code>
  <span style="font-size:11px;color:#64748B;min-width:70px;text-align:center">{dtype}</span>
  <span style="font-size:12px;color:#94A3B8;min-width:40px;text-align:center">{doc.get("page_count") or "—"}</span>
  <span style="font-size:12px;color:#94A3B8;min-width:50px;text-align:center">{doc.get("chunk_count") or "—"}</span>
  {ind_badge}
</div>"""


def table_header(*cols: str) -> str:
    cells = "".join(
        f'<div style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;'
        f'letter-spacing:.05em">{c}</div>' for c in cols
    )
    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;
  padding:8px 14px;background:#262B3D;border-radius:8px 8px 0 0;border:1px solid #2D3748;
  border-bottom:none">{cells}</div>"""


def card_wrap(html: str) -> str:
    """Wrap HTML rows in a card border."""
    return (
        f'<div style="border:1px solid #2D3748;border-radius:0 0 8px 8px;overflow:hidden">'
        f'{html}</div>'
    )


# ── Internal helpers ───────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
