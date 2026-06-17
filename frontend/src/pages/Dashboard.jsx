import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Building2, FileText, Tag, BookOpen, RefreshCw } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'

// ── Colour theme for each stat card ──────────────────────────────────────────
// Kept at module level so Tailwind's content scanner sees all class names
const THEME = {
  blue:    { border: 'border-blue-200',    text: 'text-blue-700',    bg: 'bg-blue-50' },
  indigo:  { border: 'border-indigo-200',  text: 'text-indigo-700',  bg: 'bg-indigo-50' },
  emerald: { border: 'border-emerald-200', text: 'text-emerald-700', bg: 'bg-emerald-50' },
  amber:   { border: 'border-amber-200',   text: 'text-amber-700',   bg: 'bg-amber-50' },
}

// ── Extraction status badge ───────────────────────────────────────────────────
// upload_status values from pid_drawings: uploaded | processing | completed | failed
function StatusBadge({ status }) {
  const CONFIG = {
    uploaded:   { cls: 'bg-gray-100 text-gray-600',     label: 'Uploaded' },
    processing: { cls: 'bg-yellow-100 text-yellow-700',  label: 'Processing…' },
    completed:  { cls: 'bg-green-100 text-green-700',    label: 'Complete' },
    failed:     { cls: 'bg-red-100 text-red-700',        label: 'Failed' },
  }
  const { cls, label } = CONFIG[status] ?? CONFIG.uploaded
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}

// ── Dashboard page ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { user } = useAuth()

  // 1. All process units — also drives the tag total query below
  const { data: units = [], isLoading: unitsLoading } = useQuery({
    queryKey: ['units'],
    queryFn:  () => client.get('/api/units/').then(r => r.data),
  })

  // 2. All drawings — used for the count card AND the recent drawings table
  const { data: drawings = [], isLoading: drawingsLoading } = useQuery({
    queryKey: ['drawings'],
    queryFn:  () => client.get('/api/drawings/').then(r => r.data),
  })

  // 3. All documents — only the count matters on the dashboard
  const { data: documents = [], isLoading: docsLoading } = useQuery({
    queryKey: ['documents'],
    queryFn:  () => client.get('/api/documents/').then(r => r.data),
  })

  // 4. Total tags across ALL units.
  //    Calls GET /api/tags/unit/{id}/summary for each unit in parallel then sums them.
  //    The `enabled` flag prevents this from firing before the units list has loaded.
  const { data: tagTotal = 0 } = useQuery({
    queryKey: ['tagTotal', units.map(u => u.id).join(',')],
    queryFn: async () => {
      const summaries = await Promise.all(
        units.map(u =>
          client.get(`/api/tags/unit/${u.id}/summary`).then(r => r.data)
        )
      )
      // total_tags comes from the unit summary endpoint
      return summaries.reduce((sum, s) => sum + (s.total_tags ?? 0), 0)
    },
    enabled: units.length > 0,
  })

  const isLoading = unitsLoading || drawingsLoading || docsLoading

  // Build stat card data inside the component so values are live
  const stats = [
    { label: 'Process Units',  value: units.length,     icon: Building2, ...THEME.blue },
    { label: 'P&ID Drawings',  value: drawings.length,  icon: FileText,  ...THEME.indigo },
    { label: 'Tags Extracted', value: tagTotal,         icon: Tag,       ...THEME.emerald },
    { label: 'Documents',      value: documents.length, icon: BookOpen,  ...THEME.amber },
  ]

  // Show the 10 most recent drawings (API already returns newest-first)
  const recentDrawings = drawings.slice(0, 10)

  return (
    <div>
      {/* Page header */}
      <h1 className="text-2xl font-bold text-gray-900">
        Welcome, {user?.full_name?.split(' ')[0] ?? 'Engineer'}
      </h1>
      <p className="text-gray-500 text-sm mt-1 mb-8">
        P&amp;ID Intelligence System — Numaligarh Refinery Ltd
      </p>

      {/* ── Stat cards ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, icon: Icon, border, text, bg }) => (
          <div
            key={label}
            className={`bg-white rounded-xl p-6 border ${border} shadow-sm`}
          >
            <div className={`w-10 h-10 ${bg} rounded-lg flex items-center justify-center mb-4`}>
              <Icon size={20} className={text} />
            </div>
            <p className="text-gray-500 text-sm">{label}</p>
            <p className={`text-3xl font-bold ${text} mt-1`}>
              {isLoading ? '…' : value.toLocaleString()}
            </p>
          </div>
        ))}
      </div>

      {/* ── Recent drawings table ───────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-gray-800 font-semibold text-sm">Recent Drawings Uploaded</h2>
          {!isLoading && drawings.length > 0 && (
            <span className="text-gray-400 text-xs">
              Showing {recentDrawings.length} of {drawings.length}
            </span>
          )}
        </div>

        {isLoading ? (
          // Loading spinner
          <div className="py-12 flex justify-center">
            <RefreshCw size={20} className="animate-spin text-gray-400" />
          </div>
        ) : recentDrawings.length === 0 ? (
          // Empty state
          <div className="py-12 text-center">
            <FileText size={32} className="text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No drawings uploaded yet.</p>
            <p className="text-gray-400 text-xs mt-1">
              Go to <strong>Drawings</strong> in the sidebar to upload your first P&amp;ID.
            </p>
          </div>
        ) : (
          // Data table
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-left">
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide w-20">Unit</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Drawing Number</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Title</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide text-center w-16">Pages</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide w-28">Status</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide w-28">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recentDrawings.map(d => (
                  <tr key={d.id} className="hover:bg-gray-50 transition-colors">

                    {/* Unit code badge */}
                    <td className="px-4 py-3">
                      <span className="bg-slate-100 text-slate-700 text-xs font-semibold px-2 py-0.5 rounded">
                        {d.unit_code}
                      </span>
                    </td>

                    {/* Drawing number in monospace */}
                    <td className="px-4 py-3 font-mono text-xs text-gray-800 whitespace-nowrap">
                      {d.drawing_number}
                    </td>

                    {/* Title — truncated if long */}
                    <td className="px-4 py-3 text-gray-600 max-w-xs">
                      <span className="block truncate">{d.drawing_title ?? '—'}</span>
                    </td>

                    {/* Page count */}
                    <td className="px-4 py-3 text-gray-600 text-center">
                      {d.total_pages ?? d.page_count ?? '—'}
                    </td>

                    {/* Extraction status badge */}
                    <td className="px-4 py-3">
                      <StatusBadge status={d.upload_status} />
                    </td>

                    {/* Upload date */}
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {new Date(d.uploaded_at).toLocaleDateString('en-IN', {
                        day: '2-digit', month: 'short', year: 'numeric',
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
