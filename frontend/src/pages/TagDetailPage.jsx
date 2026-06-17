import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft, Printer, Tag, FileText, BookOpen,
  Wrench, Activity, GitBranch, AlertCircle, Loader2,
  ArrowUpRight, ArrowDownRight, ArrowRight,
} from 'lucide-react'
import client from '../api/client'

// ── Color scheme per tag category ─────────────────────────────────────────────
// Used to set the hero card color, section borders, and badge colors.
const CATEGORY_STYLE = {
  EQUIPMENT:  {
    heroBg:    'bg-blue-600',
    heroText:  'text-white',
    lightBg:   'bg-blue-50',
    border:    'border-blue-200',
    textColor: 'text-blue-700',
    icon:      Wrench,
  },
  INSTRUMENT: {
    heroBg:    'bg-green-600',
    heroText:  'text-white',
    lightBg:   'bg-green-50',
    border:    'border-green-200',
    textColor: 'text-green-700',
    icon:      Activity,
  },
  LINE: {
    heroBg:    'bg-orange-500',
    heroText:  'text-white',
    lightBg:   'bg-orange-50',
    border:    'border-orange-200',
    textColor: 'text-orange-700',
    icon:      GitBranch,
  },
}

// Fallback for unexpected categories
const DEFAULT_STYLE = CATEGORY_STYLE.EQUIPMENT

// ── Human-readable field labels ────────────────────────────────────────────────
// Maps database column names to user-friendly display labels.
const FIELD_LABELS = {
  service:          'Service',
  design_pressure:  'Design Pressure',
  design_temp:      'Design Temperature',
  capacity:         'Capacity',
  material:         'Material',
  notes:            'Notes',
  process_variable: 'Process Variable',
  range_low:        'Range (Low)',
  range_high:       'Range (High)',
  unit_of_measure:  'Unit of Measure',
  nominal_diameter: 'Nominal Diameter',
  fluid_service:    'Fluid Service',
  line_sequence:    'Line Sequence',
  pressure_class:   'Pressure Class',
  pipe_spec:        'Pipe Spec',
  from_equipment:   'From Equipment',
  to_equipment:     'To Equipment',
  insulation_code:  'Insulation Code',
  tracing_code:     'Tracing Code',
}

// Fields we don't show in the detail table (shown in other sections already)
const SKIP_FIELDS = new Set([
  'tag_number', 'tag_type', 'tag_category', 'description',
  'unit_id', 'unit_code', 'unit_name',
  'drawing_number', 'drawing_title', 'revision', 'page_number',
])

// ── Document type badge ────────────────────────────────────────────────────────
const DOC_TYPE_CONFIG = {
  OPERATING_MANUAL:       { cls: 'bg-blue-50 text-blue-700',    label: 'Operating Manual' },
  SOP:                    { cls: 'bg-purple-50 text-purple-700', label: 'SOP' },
  MAINTENANCE_PROCEDURE:  { cls: 'bg-orange-50 text-orange-700', label: 'Maintenance' },
  SAFETY:                 { cls: 'bg-red-50 text-red-700',       label: 'Safety' },
}

function DocTypeBadge({ docType }) {
  const cfg = DOC_TYPE_CONFIG[docType] ?? { cls: 'bg-gray-100 text-gray-600', label: docType ?? 'Document' }
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  )
}

// ── Section header ─────────────────────────────────────────────────────────────
function SectionHeader({ icon: Icon, title, count }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon size={15} className="text-gray-400" />
      <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">{title}</h2>
      {count !== undefined && (
        <span className="bg-gray-100 text-gray-600 text-xs rounded-full px-2 py-0.5">{count}</span>
      )}
    </div>
  )
}

// ── Connectivity table ─────────────────────────────────────────────────────────
// Shared component for both upstream and downstream sections.
// Rows are clickable — navigate to that tag's detail page.
function ConnectivityTable({ tags, navigate, emptyMsg }) {
  if (tags.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic py-2">{emptyMsg}</p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-white/60">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-white/40 text-left">
            <th className="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Tag</th>
            <th className="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Type</th>
            <th className="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Description</th>
            <th className="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Via Line</th>
            <th className="w-6" />
          </tr>
        </thead>
        <tbody className="divide-y divide-white/50">
          {tags.map(t => (
            <tr
              key={t.tag_number}
              onClick={() => navigate(`/tags/${encodeURIComponent(t.tag_number)}`)}
              className="cursor-pointer hover:bg-white/50 transition-colors group"
            >
              <td className="px-3 py-2 font-mono text-xs font-bold text-gray-800">{t.tag_number}</td>
              <td className="px-3 py-2 text-gray-500 text-xs">{t.tag_type || '—'}</td>
              <td className="px-3 py-2 text-gray-600 text-xs max-w-xs">
                <span className="block truncate">{t.description || '—'}</span>
              </td>
              <td className="px-3 py-2 font-mono text-xs text-gray-400">{t.via_line || '—'}</td>
              <td className="px-2 py-2 text-gray-300 group-hover:text-gray-500 transition-colors">
                <ArrowRight size={12} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


// ── Tag Detail page ────────────────────────────────────────────────────────────
export default function TagDetailPage() {
  const { tagNumber } = useParams()
  const navigate      = useNavigate()

  const {
    data:      tag,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['tagDetail', tagNumber],
    queryFn:  () =>
      client.get(`/api/tags/${encodeURIComponent(tagNumber)}`).then(r => r.data),
  })

  // ── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 size={28} className="animate-spin text-gray-400" />
      </div>
    )
  }

  // ── Error / not found ──────────────────────────────────────────────────────
  if (error) {
    const is404 = error.response?.status === 404
    return (
      <div className="max-w-2xl mx-auto">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700 text-sm mb-6 transition-colors"
        >
          <ArrowLeft size={15} /> Back
        </button>
        <div className="text-center py-16 bg-white rounded-2xl border border-gray-200">
          <Tag size={48} className="text-gray-200 mx-auto mb-4" />
          <p className="text-gray-700 font-semibold text-lg">
            {is404 ? 'Tag not found' : 'Failed to load tag'}
          </p>
          <p className="text-gray-400 text-sm mt-2 max-w-xs mx-auto">
            {is404
              ? `No tag "${tagNumber}" was found in any unit. Check the tag number and try again.`
              : (error.response?.data?.detail ?? 'An unexpected error occurred.')}
          </p>
          <button
            onClick={() => navigate('/tags/search')}
            className="mt-6 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
          >
            Back to Tag Search
          </button>
        </div>
      </div>
    )
  }

  if (!tag) return null

  // ── Resolve category style ─────────────────────────────────────────────────
  const style = CATEGORY_STYLE[tag.tag_category] ?? DEFAULT_STYLE

  // ── Build detail field rows ────────────────────────────────────────────────
  // Show fields from the `details` object with human-readable labels.
  // Skip null, empty, and internal fields.
  const detailRows = Object.entries(tag.details ?? {})
    .filter(([k, v]) => !SKIP_FIELDS.has(k) && v !== null && v !== '' && v !== undefined)
    .map(([k, v]) => ({ label: FIELD_LABELS[k] ?? k.replace(/_/g, ' '), value: String(v) }))

  return (
    <div className="max-w-5xl mx-auto">

      {/* ── Back navigation + print button ───────────────────────────── */}
      <div className="flex items-center justify-between mb-4 print:hidden">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700 text-sm transition-colors"
        >
          <ArrowLeft size={15} /> Back
        </button>
        <button
          onClick={() => window.print()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300
                     text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <Printer size={14} /> Print
        </button>
      </div>

      {/* ── Hero card — tag number in a prominent colored box ─────────── */}
      <div className={`${style.lightBg} ${style.border} border rounded-2xl p-5 mb-5`}>
        <div className="flex items-start gap-4 flex-wrap">

          {/* Large tag number badge */}
          <div className={`${style.heroBg} ${style.heroText} px-5 py-3 rounded-xl flex-shrink-0 shadow-sm`}>
            <span className="text-2xl font-bold font-mono tracking-wide">{tag.tag_number}</span>
          </div>

          {/* Category + description */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              {/* Tag category badge */}
              <span className={`text-xs font-medium ${style.textColor} bg-white border ${style.border}
                               px-2.5 py-1 rounded-full`}>
                {tag.tag_category}
              </span>
              {/* Tag type */}
              {tag.tag_type && (
                <span className="text-xs text-gray-500 bg-white border border-gray-200 px-2.5 py-1 rounded-full">
                  {tag.tag_type}
                </span>
              )}
              {/* Unit code */}
              <span className="bg-slate-700 text-white text-xs font-semibold px-2.5 py-1 rounded-full">
                {tag.unit?.unit_code}
              </span>
            </div>

            {/* Description */}
            <p className="text-gray-800 font-medium">
              {tag.description || <span className="text-gray-400 italic">No description</span>}
            </p>
            {/* Unit name */}
            <p className="text-gray-400 text-xs mt-0.5">{tag.unit?.unit_name}</p>
          </div>
        </div>
      </div>

      {/* ── Main content grid ─────────────────────────────────────────── */}
      <div className="space-y-4">

        {/* ── Section 1: Tag Information ─────────────────────────────── */}
        {detailRows.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <SectionHeader icon={Tag} title="Tag Information" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-3 gap-x-6">
              {detailRows.map(({ label, value }) => (
                <div key={label} className="flex flex-col sm:flex-row sm:items-baseline gap-1">
                  <span className="text-xs font-medium text-gray-500 uppercase tracking-wide sm:w-40 flex-shrink-0">
                    {label}
                  </span>
                  <span className="text-sm text-gray-800 font-mono break-all">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Section 2: Found in Drawings ───────────────────────────── */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <SectionHeader icon={FileText} title="Found in Drawings" count={tag.drawings?.length ?? 0} />
          {!tag.drawings?.length ? (
            <p className="text-gray-400 text-sm italic">Drawing information not available.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="pb-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Drawing Number</th>
                    <th className="pb-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Title</th>
                    <th className="pb-2 text-xs font-medium text-gray-500 uppercase tracking-wide w-16">Rev</th>
                    <th className="pb-2 text-xs font-medium text-gray-500 uppercase tracking-wide text-center w-14">Page</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {tag.drawings.map((d, i) => (
                    <tr key={i} className="hover:bg-gray-50 transition-colors">
                      <td className="py-2.5 pr-4 font-mono text-xs font-semibold text-gray-800">
                        {d.drawing_number}
                      </td>
                      <td className="py-2.5 pr-4 text-gray-600 max-w-xs">
                        <span className="block truncate">{d.drawing_title || '—'}</span>
                      </td>
                      <td className="py-2.5 pr-4 font-mono text-xs text-gray-400">{d.revision || '—'}</td>
                      <td className="py-2.5 text-gray-500 text-center">{d.page_number}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── Sections 3 + 4: Upstream & Downstream — side by side ──── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

          {/* Section 3: Upstream (blue-tinted panel) */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <ArrowUpRight size={16} className="text-blue-500" />
              <h2 className="text-sm font-semibold text-blue-700 uppercase tracking-wide">
                Upstream Equipment
              </h2>
              <span className="bg-blue-100 text-blue-600 text-xs rounded-full px-2 py-0.5">
                {tag.upstream_tags?.length ?? 0}
              </span>
            </div>
            <ConnectivityTable
              tags={tag.upstream_tags ?? []}
              navigate={navigate}
              emptyMsg="No upstream connections found"
            />
          </div>

          {/* Section 4: Downstream (green-tinted panel) */}
          <div className="bg-green-50 border border-green-200 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <ArrowDownRight size={16} className="text-green-500" />
              <h2 className="text-sm font-semibold text-green-700 uppercase tracking-wide">
                Downstream Equipment
              </h2>
              <span className="bg-green-100 text-green-600 text-xs rounded-full px-2 py-0.5">
                {tag.downstream_tags?.length ?? 0}
              </span>
            </div>
            <ConnectivityTable
              tags={tag.downstream_tags ?? []}
              navigate={navigate}
              emptyMsg="No downstream connections found"
            />
          </div>
        </div>

        {/* ── Section 5: Document References ────────────────────────── */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <SectionHeader
            icon={BookOpen}
            title="References in Operating Manuals & SOPs"
            count={tag.document_references?.length ?? 0}
          />

          {!tag.document_references?.length ? (
            // Empty state — guide the user to upload documents
            <div className="py-6 text-center border border-dashed border-gray-200 rounded-lg">
              <BookOpen size={32} className="text-gray-200 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">No manual references found.</p>
              <p className="text-gray-400 text-xs mt-1 max-w-sm mx-auto">
                Upload and index operating manuals or SOPs in the{' '}
                <button
                  onClick={() => navigate('/documents')}
                  className="text-blue-500 hover:underline"
                >
                  Documents
                </button>{' '}
                section to see references here.
              </p>
            </div>
          ) : (
            // Reference cards
            <div className="space-y-3">
              {tag.document_references.map((ref, i) => (
                <div
                  key={i}
                  className="border border-gray-200 rounded-lg overflow-hidden"
                >
                  {/* Card header — document title + type */}
                  <div className="flex items-start justify-between gap-3 bg-gray-50 px-4 py-2.5 border-b border-gray-200">
                    <div className="flex items-center gap-2 min-w-0">
                      <BookOpen size={14} className="text-gray-400 flex-shrink-0" />
                      <span className="text-sm font-medium text-gray-700 truncate">
                        {ref.doc_title || 'Untitled Document'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {ref.doc_type && <DocTypeBadge docType={ref.doc_type} />}
                      {ref.page_number && (
                        <span className="text-xs text-gray-400">p. {ref.page_number}</span>
                      )}
                    </div>
                  </div>

                  {/* Card body — section + context */}
                  <div className="px-4 py-3">
                    {ref.section_title && (
                      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">
                        {ref.section_title}
                      </p>
                    )}
                    {ref.context_text ? (
                      // Context paragraph in a blockquote style
                      <blockquote className="border-l-2 border-blue-300 pl-3 text-sm text-gray-600 leading-relaxed italic">
                        {ref.context_text}
                      </blockquote>
                    ) : (
                      <p className="text-gray-400 text-xs italic">No context text available.</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
