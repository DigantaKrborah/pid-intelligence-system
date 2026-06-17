import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Download, FileText, Wrench, Activity, GitBranch, Share2,
  Loader2, AlertCircle, CheckCircle2, XCircle, Clock, Zap,
} from 'lucide-react'
import client from '../api/client'
import ExtractionModal from '../components/ExtractionModal'

// ── Client-side CSV download ───────────────────────────────────────────────────
// columns = [{ key: 'field_name', label: 'Column Header' }, ...]
function downloadCsv(rows, filename, columns) {
  const header = columns.map(c => c.label).join(',')
  const body   = rows.map(row =>
    columns.map(c =>
      `"${(row[c.key] ?? '').toString().replace(/"/g, '""')}"`
    ).join(',')
  )
  const csv  = [header, ...body].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// ── Extraction status badge (for page cards and table cells) ──────────────────
function ExtractionBadge({ status }) {
  const MAP = {
    pending:    { cls: 'bg-gray-100 text-gray-500',     label: 'Pending',      icon: <Clock size={11} /> },
    processing: { cls: 'bg-yellow-100 text-yellow-700', label: 'Processing…',  icon: <Loader2 size={11} className="animate-spin" /> },
    completed:  { cls: 'bg-green-100 text-green-700',   label: 'Extracted',    icon: <CheckCircle2 size={11} /> },
    failed:     { cls: 'bg-red-100 text-red-700',       label: 'Failed',       icon: <XCircle size={11} /> },
  }
  const { cls, label, icon } = MAP[status] ?? MAP.pending
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {icon}{label}
    </span>
  )
}

// ── Tab definitions ────────────────────────────────────────────────────────────
const TABS = [
  { key: 'pages',        label: 'Pages',            Icon: FileText  },
  { key: 'equipment',    label: 'Equipment Tags',    Icon: Wrench    },
  { key: 'instruments',  label: 'Instrument Tags',   Icon: Activity  },
  { key: 'lines',        label: 'Line Specs',        Icon: GitBranch },
  { key: 'connectivity', label: 'Connectivity',      Icon: Share2    },
]

// ── Empty state for tabs with no data ─────────────────────────────────────────
function EmptyTabState({ label }) {
  return (
    <div className="py-16 text-center">
      <p className="text-gray-400 text-sm">
        No {label.toLowerCase()} found for this drawing.
        Run AI extraction to populate this data.
      </p>
    </div>
  )
}

// ── DrawingDetailPage ──────────────────────────────────────────────────────────
export default function DrawingDetailPage() {
  const { id }      = useParams()
  const navigate    = useNavigate()
  const queryClient = useQueryClient()

  const [activeTab, setActiveTab]           = useState('pages')
  const [showExtraction, setShowExtraction] = useState(false)

  // ── Drawing info + pages ───────────────────────────────────────────────────
  const {
    data: drawing,
    isLoading: drawingLoading,
    error: drawingError,
  } = useQuery({
    queryKey: ['drawing', id],
    queryFn:  () => client.get(`/api/drawings/${id}`).then(r => r.data),
  })

  // ── Extracted tags (available after AI extraction runs) ───────────────────
  const {
    data: tags = { equipment: [], instruments: [], lines: [], connectivity: [] },
    isLoading: tagsLoading,
    refetch: refetchTags,
  } = useQuery({
    queryKey: ['drawingTags', id],
    queryFn:  () => client.get(`/api/drawings/${id}/tags`).then(r => r.data),
    enabled:  !!drawing,   // wait until drawing row is loaded
  })

  // After extraction finishes, refresh both the drawing (page statuses) and tags
  function handleExtractionDone() {
    queryClient.invalidateQueries({ queryKey: ['drawing', id] })
    queryClient.invalidateQueries({ queryKey: ['drawingTags', id] })
    setShowExtraction(false)
  }

  // ── Loading state ──────────────────────────────────────────────────────────
  if (drawingLoading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 size={28} className="animate-spin text-gray-400" />
      </div>
    )
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (drawingError) {
    return (
      <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4 mt-4">
        <AlertCircle size={18} className="text-red-500 flex-shrink-0" />
        <p className="text-red-700 text-sm">
          {drawingError.response?.data?.detail ?? 'Failed to load drawing.'}
        </p>
      </div>
    )
  }

  if (!drawing) return null

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div>
      {/* ── Back navigation ──────────────────────────────────────────────── */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700 text-sm mb-4 transition-colors"
      >
        <ArrowLeft size={15} />
        Back to Drawings
      </button>

      {/* ── Drawing header card ───────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 mb-5">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            {/* Unit badge + revision */}
            <div className="flex items-center gap-2 mb-1.5">
              <span className="bg-slate-100 text-slate-700 text-xs font-bold px-2 py-0.5 rounded">
                {drawing.unit_code}
              </span>
              {drawing.revision && (
                <span className="bg-blue-50 text-blue-700 text-xs font-mono px-2 py-0.5 rounded">
                  {drawing.revision}
                </span>
              )}
              <ExtractionBadge status={drawing.upload_status} />
            </div>

            {/* Drawing number */}
            <h1 className="text-lg font-bold text-gray-900 font-mono">
              {drawing.drawing_number}
            </h1>

            {/* Title + unit name */}
            {drawing.drawing_title && (
              <p className="text-gray-600 text-sm mt-0.5">{drawing.drawing_title}</p>
            )}
            <p className="text-gray-400 text-xs mt-1">{drawing.unit_name}</p>
          </div>

          {/* Extract button */}
          {drawing.upload_status !== 'failed' && (
            <button
              onClick={() => setShowExtraction(true)}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-600
                         text-white text-sm font-medium rounded-lg transition-colors shadow-sm"
            >
              <Zap size={15} />
              {drawing.upload_status === 'processing' ? 'View Extraction…' : 'Extract Tags'}
            </button>
          )}
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-6 mt-4 pt-4 border-t border-gray-100 text-sm">
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-800">{drawing.total_pages ?? 0}</p>
            <p className="text-gray-400 text-xs mt-0.5">Pages</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-700">{tags.equipment.length}</p>
            <p className="text-gray-400 text-xs mt-0.5">Equipment</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-700">{tags.instruments.length}</p>
            <p className="text-gray-400 text-xs mt-0.5">Instruments</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-emerald-700">{tags.lines.length}</p>
            <p className="text-gray-400 text-xs mt-0.5">Lines</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-orange-700">{tags.connectivity.length}</p>
            <p className="text-gray-400 text-xs mt-0.5">Connections</p>
          </div>
        </div>
      </div>

      {/* ── Tab bar ───────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {/* Tab headers */}
        <div className="flex border-b border-gray-100 overflow-x-auto">
          {TABS.map(({ key, label, Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium whitespace-nowrap
                transition-colors border-b-2 -mb-px
                ${activeTab === key
                  ? 'border-blue-600 text-blue-700 bg-blue-50/50'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
            >
              <Icon size={14} />
              {label}
              {/* Show count badge on tag tabs */}
              {key === 'equipment'    && tags.equipment.length > 0    && <CountBadge n={tags.equipment.length} />}
              {key === 'instruments'  && tags.instruments.length > 0  && <CountBadge n={tags.instruments.length} />}
              {key === 'lines'        && tags.lines.length > 0        && <CountBadge n={tags.lines.length} />}
              {key === 'connectivity' && tags.connectivity.length > 0 && <CountBadge n={tags.connectivity.length} />}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="p-0">
          {activeTab === 'pages'        && <PagesTab        pages={drawing.pages ?? []}                        drawingNumber={drawing.drawing_number} />}
          {activeTab === 'equipment'    && <EquipmentTab    rows={tags.equipment}   loading={tagsLoading}      drawingNumber={drawing.drawing_number} />}
          {activeTab === 'instruments'  && <InstrumentsTab  rows={tags.instruments} loading={tagsLoading}      drawingNumber={drawing.drawing_number} />}
          {activeTab === 'lines'        && <LinesTab        rows={tags.lines}       loading={tagsLoading}      drawingNumber={drawing.drawing_number} />}
          {activeTab === 'connectivity' && <ConnectivityTab rows={tags.connectivity} loading={tagsLoading}     drawingNumber={drawing.drawing_number} />}
        </div>
      </div>

      {/* ── Extraction modal ──────────────────────────────────────────────── */}
      {showExtraction && (
        <ExtractionModal
          drawing={drawing}
          onClose={() => setShowExtraction(false)}
          onDone={handleExtractionDone}
        />
      )}
    </div>
  )
}

// ── Small helpers ──────────────────────────────────────────────────────────────

function CountBadge({ n }) {
  return (
    <span className="bg-gray-200 text-gray-600 text-xs rounded-full px-1.5 py-0.5 leading-none">
      {n}
    </span>
  )
}

// Shared export button used on every tab
function ExportButton({ onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-gray-300
                 text-gray-600 hover:bg-gray-50 rounded-lg transition-colors disabled:opacity-30
                 disabled:cursor-not-allowed"
    >
      <Download size={13} />
      Export CSV
    </button>
  )
}

// ── Tab: Pages ─────────────────────────────────────────────────────────────────
// Shows a grid of cards — one per page — with extraction status badge.
// (Thumbnail images are not displayed; they reside on the server's local disk.)

function PagesTab({ pages, drawingNumber }) {
  function exportCsv() {
    downloadCsv(pages, `${drawingNumber}_pages.csv`, [
      { key: 'page_number',       label: 'Page' },
      { key: 'extraction_status', label: 'Status' },
      { key: 'extraction_model',  label: 'Model Used' },
      { key: 'extracted_at',      label: 'Extracted At' },
    ])
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs text-gray-400">{pages.length} page{pages.length !== 1 ? 's' : ''}</p>
        <ExportButton onClick={exportCsv} disabled={pages.length === 0} />
      </div>

      {pages.length === 0 ? (
        <p className="py-12 text-center text-gray-400 text-sm">No page data found.</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {pages.map(page => (
            <div
              key={page.id}
              className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center"
            >
              {/* Page number as large display — no thumbnail available from file server */}
              <div className="w-full aspect-[3/4] bg-gray-200 rounded flex items-center justify-center mb-2">
                <span className="text-2xl font-bold text-gray-400">{page.page_number}</span>
              </div>
              <p className="text-xs text-gray-500 mb-1.5">Page {page.page_number}</p>
              <ExtractionBadge status={page.extraction_status} />
              {page.extracted_at && (
                <p className="text-gray-300 text-xs mt-1">
                  {new Date(page.extracted_at).toLocaleDateString('en-IN', {
                    day: '2-digit', month: 'short',
                  })}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Tab: Equipment Tags ────────────────────────────────────────────────────────
function EquipmentTab({ rows, loading, drawingNumber }) {
  function exportCsv() {
    downloadCsv(rows, `${drawingNumber}_equipment.csv`, [
      { key: 'tag_number',      label: 'Tag Number' },
      { key: 'tag_type',        label: 'Type' },
      { key: 'description',     label: 'Description' },
      { key: 'service',         label: 'Service' },
      { key: 'design_pressure', label: 'Design Pressure' },
      { key: 'design_temp',     label: 'Design Temp' },
      { key: 'capacity',        label: 'Capacity' },
      { key: 'material',        label: 'Material' },
      { key: 'page_number',     label: 'Page' },
      { key: 'notes',           label: 'Notes' },
    ])
  }

  if (loading) return <LoadingTab />
  if (rows.length === 0) return (
    <div className="p-4">
      <div className="flex justify-end mb-3">
        <ExportButton disabled />
      </div>
      <EmptyTabState label="Equipment Tags" />
    </div>
  )

  return (
    <div>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <p className="text-xs text-gray-400">{rows.length} tag{rows.length !== 1 ? 's' : ''}</p>
        <ExportButton onClick={exportCsv} />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100 text-left">
              <Th>Tag Number</Th>
              <Th>Type</Th>
              <Th>Description</Th>
              <Th>Service</Th>
              <Th>Design P</Th>
              <Th>Design T</Th>
              <Th>Page</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((r, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <Td mono>{r.tag_number}</Td>
                <Td>{r.tag_type || '—'}</Td>
                <Td>{r.description || '—'}</Td>
                <Td>{r.service || '—'}</Td>
                <Td>{r.design_pressure || '—'}</Td>
                <Td>{r.design_temp || '—'}</Td>
                <Td center>{r.page_number}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Tab: Instrument Tags ───────────────────────────────────────────────────────
function InstrumentsTab({ rows, loading, drawingNumber }) {
  function exportCsv() {
    downloadCsv(rows, `${drawingNumber}_instruments.csv`, [
      { key: 'tag_number',       label: 'Tag Number' },
      { key: 'instrument_type',  label: 'Instrument Type' },
      { key: 'description',      label: 'Description' },
      { key: 'process_variable', label: 'Process Variable' },
      { key: 'service',          label: 'Service' },
      { key: 'range_low',        label: 'Range Low' },
      { key: 'range_high',       label: 'Range High' },
      { key: 'unit_of_measure',  label: 'Unit' },
      { key: 'page_number',      label: 'Page' },
      { key: 'notes',            label: 'Notes' },
    ])
  }

  if (loading) return <LoadingTab />
  if (rows.length === 0) return (
    <div className="p-4">
      <div className="flex justify-end mb-3"><ExportButton disabled /></div>
      <EmptyTabState label="Instrument Tags" />
    </div>
  )

  return (
    <div>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <p className="text-xs text-gray-400">{rows.length} tag{rows.length !== 1 ? 's' : ''}</p>
        <ExportButton onClick={exportCsv} />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100 text-left">
              <Th>Tag Number</Th>
              <Th>Type</Th>
              <Th>Description</Th>
              <Th>Process Variable</Th>
              <Th>Range</Th>
              <Th>Unit</Th>
              <Th>Page</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((r, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <Td mono>{r.tag_number}</Td>
                <Td>{r.instrument_type || '—'}</Td>
                <Td>{r.description || '—'}</Td>
                <Td>{r.process_variable || '—'}</Td>
                <Td>
                  {r.range_low || r.range_high
                    ? `${r.range_low ?? ''} – ${r.range_high ?? ''}`
                    : '—'}
                </Td>
                <Td>{r.unit_of_measure || '—'}</Td>
                <Td center>{r.page_number}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Tab: Line Specs ────────────────────────────────────────────────────────────
function LinesTab({ rows, loading, drawingNumber }) {
  function exportCsv() {
    downloadCsv(rows, `${drawingNumber}_lines.csv`, [
      { key: 'line_number',      label: 'Line Number' },
      { key: 'nominal_diameter', label: 'Diameter' },
      { key: 'fluid_service',    label: 'Fluid Service' },
      { key: 'pressure_class',   label: 'Pressure Class' },
      { key: 'pipe_spec',        label: 'Pipe Spec' },
      { key: 'from_equipment',   label: 'From' },
      { key: 'to_equipment',     label: 'To' },
      { key: 'insulation_code',  label: 'Insulation' },
      { key: 'tracing_code',     label: 'Tracing' },
      { key: 'page_number',      label: 'Page' },
      { key: 'notes',            label: 'Notes' },
    ])
  }

  if (loading) return <LoadingTab />
  if (rows.length === 0) return (
    <div className="p-4">
      <div className="flex justify-end mb-3"><ExportButton disabled /></div>
      <EmptyTabState label="Line Specs" />
    </div>
  )

  return (
    <div>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <p className="text-xs text-gray-400">{rows.length} line{rows.length !== 1 ? 's' : ''}</p>
        <ExportButton onClick={exportCsv} />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100 text-left">
              <Th>Line Number</Th>
              <Th>Dia.</Th>
              <Th>Fluid Service</Th>
              <Th>Pressure Class</Th>
              <Th>Pipe Spec</Th>
              <Th>From</Th>
              <Th>To</Th>
              <Th>Page</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((r, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <Td mono>{r.line_number}</Td>
                <Td>{r.nominal_diameter || '—'}</Td>
                <Td>{r.fluid_service || '—'}</Td>
                <Td>{r.pressure_class || '—'}</Td>
                <Td mono>{r.pipe_spec || '—'}</Td>
                <Td>{r.from_equipment || '—'}</Td>
                <Td>{r.to_equipment || '—'}</Td>
                <Td center>{r.page_number}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Tab: Connectivity ──────────────────────────────────────────────────────────
function ConnectivityTab({ rows, loading, drawingNumber }) {
  function exportCsv() {
    downloadCsv(rows, `${drawingNumber}_connectivity.csv`, [
      { key: 'source_tag',       label: 'Source Tag' },
      { key: 'source_tag_type',  label: 'Source Type' },
      { key: 'direction',        label: 'Direction' },
      { key: 'target_tag',       label: 'Target Tag' },
      { key: 'target_tag_type',  label: 'Target Type' },
      { key: 'via_line',         label: 'Via Line' },
    ])
  }

  if (loading) return <LoadingTab />
  if (rows.length === 0) return (
    <div className="p-4">
      <div className="flex justify-end mb-3"><ExportButton disabled /></div>
      <EmptyTabState label="Connectivity" />
    </div>
  )

  return (
    <div>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <p className="text-xs text-gray-400">{rows.length} connection{rows.length !== 1 ? 's' : ''}</p>
        <ExportButton onClick={exportCsv} />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100 text-left">
              <Th>Source Tag</Th>
              <Th>Type</Th>
              <Th>→</Th>
              <Th>Target Tag</Th>
              <Th>Type</Th>
              <Th>Via Line</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((r, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <Td mono>{r.source_tag}</Td>
                <Td><TypeChip type={r.source_tag_type} /></Td>
                <td className="px-3 py-2.5 text-gray-300">→</td>
                <Td mono>{r.target_tag}</Td>
                <Td><TypeChip type={r.target_tag_type} /></Td>
                <Td mono>{r.via_line || '—'}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Tiny tag-type pill ─────────────────────────────────────────────────────────
function TypeChip({ type }) {
  const COLOR = {
    EQUIPMENT:  'bg-blue-50 text-blue-700',
    INSTRUMENT: 'bg-purple-50 text-purple-700',
    LINE:       'bg-emerald-50 text-emerald-700',
  }
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${COLOR[type] ?? 'bg-gray-100 text-gray-600'}`}>
      {type ?? '—'}
    </span>
  )
}

// ── Table cell / header primitives ─────────────────────────────────────────────
function Th({ children }) {
  return (
    <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
      {children}
    </th>
  )
}
function Td({ children, mono = false, center = false }) {
  return (
    <td className={`px-4 py-2.5 text-gray-600 max-w-xs
      ${mono   ? 'font-mono text-xs text-gray-800' : ''}
      ${center ? 'text-center' : ''}
    `}>
      <span className="block truncate">{children}</span>
    </td>
  )
}

// ── Loading placeholder ────────────────────────────────────────────────────────
function LoadingTab() {
  return (
    <div className="flex justify-center py-12">
      <Loader2 size={20} className="animate-spin text-gray-400" />
    </div>
  )
}
