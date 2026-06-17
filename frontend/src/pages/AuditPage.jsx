import React, { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ClipboardList, Download, ChevronLeft, ChevronRight,
  AlertCircle, Loader2, ChevronDown, Filter,
} from 'lucide-react'
import client from '../api/client'

const PAGE_LIMIT = 50

// ── Action badge ──────────────────────────────────────────────────────────────
// Different action types get different colours to help operators scan the log.
const ACTION_COLORS = {
  LOGIN:             'bg-gray-100 text-gray-600',
  LOGOUT:            'bg-gray-100 text-gray-500',
  CREATE_UNIT:       'bg-blue-100 text-blue-700',
  UPDATE_UNIT:       'bg-blue-50 text-blue-600',
  UPLOAD_DRAWING:    'bg-indigo-100 text-indigo-700',
  DELETE_DRAWING:    'bg-red-100 text-red-700',
  START_EXTRACTION:  'bg-yellow-100 text-yellow-700',
  UPLOAD_DOCUMENT:   'bg-purple-100 text-purple-700',
  INDEX_DOCUMENT:    'bg-purple-50 text-purple-600',
  DELETE_DOCUMENT:   'bg-red-50 text-red-600',
  UPDATE_SETTINGS:   'bg-orange-100 text-orange-700',
  CREATE_USER:       'bg-teal-100 text-teal-700',
  TOGGLE_USER:       'bg-teal-50 text-teal-600',
}
function ActionBadge({ action }) {
  const cls = ACTION_COLORS[action] ?? 'bg-gray-100 text-gray-600'
  const label = action?.replace(/_/g, ' ')
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${cls}`}>
      {label}
    </span>
  )
}

// ── Compact JSON display ───────────────────────────────────────────────────────
function DetailsCell({ details }) {
  if (!details) return <span className="text-gray-300 text-xs">—</span>
  let parsed = details
  if (typeof details === 'string') {
    try { parsed = JSON.parse(details) } catch { return <span className="text-gray-500 text-xs">{details}</span> }
  }
  const entries = Object.entries(parsed)
  if (!entries.length) return <span className="text-gray-300 text-xs">—</span>
  return (
    <div className="flex flex-wrap gap-1">
      {entries.slice(0, 4).map(([k, v]) => (
        <span key={k} className="text-xs text-gray-500">
          <span className="text-gray-400">{k}:</span>{' '}
          <span className="font-mono">{String(v).slice(0, 40)}</span>
        </span>
      ))}
      {entries.length > 4 && <span className="text-xs text-gray-300">+{entries.length - 4} more</span>}
    </div>
  )
}

// ── CSV export helper ─────────────────────────────────────────────────────────
function exportCsv(rows) {
  const headers = ['Timestamp', 'Username', 'Full Name', 'Action', 'Entity Type', 'Entity ID', 'Details']
  const body = rows.map(r => [
    r.created_at ? new Date(r.created_at).toISOString() : '',
    r.username ?? '',
    r.full_name ?? '',
    r.action ?? '',
    r.entity_type ?? '',
    r.entity_id ?? '',
    typeof r.details === 'object' ? JSON.stringify(r.details) : (r.details ?? ''),
  ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(','))

  const csv = [headers.join(','), ...body].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `audit_log_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ── Audit Page ────────────────────────────────────────────────────────────────
export default function AuditPage() {
  const [dateFrom,  setDateFrom]  = useState('')
  const [dateTo,    setDateTo]    = useState('')
  const [action,    setAction]    = useState('')
  const [userId,    setUserId]    = useState('')
  const [offset,    setOffset]    = useState(0)

  // Reset to page 0 whenever any filter changes
  function updateFilter(setter) {
    return (val) => { setter(val); setOffset(0) }
  }

  // Build query string
  const params = new URLSearchParams({ limit: PAGE_LIMIT, offset })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo)   params.set('date_to',   dateTo)
  if (action)   params.set('action',    action)
  if (userId)   params.set('user_id',   userId)

  const { data: logs = [], isLoading, error } = useQuery({
    queryKey: ['audit', dateFrom, dateTo, action, userId, offset],
    queryFn:  () => client.get(`/api/audit/?${params}`).then(r => r.data),
  })

  const { data: users = [] } = useQuery({
    queryKey: ['users'],
    queryFn:  () => client.get('/api/users/').then(r => r.data),
  })

  // Unique action types from this page — populate the action dropdown
  const { data: actionTypes = [] } = useQuery({
    queryKey: ['audit-action-types'],
    queryFn:  () =>
      client.get('/api/audit/?limit=500&offset=0').then(r =>
        [...new Set((r.data ?? []).map(e => e.action).filter(Boolean))].sort()
      ),
    staleTime: 60_000,
  })

  const hasPrev = offset > 0
  const hasNext = logs.length === PAGE_LIMIT

  const currentPage = Math.floor(offset / PAGE_LIMIT) + 1

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
          <p className="text-gray-500 text-sm mt-1">All system actions recorded for compliance</p>
        </div>
        <button onClick={() => exportCsv(logs)} disabled={logs.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50
                     disabled:opacity-40 text-gray-700 text-sm font-medium rounded-lg transition-colors shadow-sm">
          <Download size={14} />
          Export CSV
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3 bg-white rounded-xl border border-gray-200 shadow-sm px-4 py-3 mb-4">
        <Filter size={14} className="text-gray-400 flex-shrink-0" />

        {/* Date range */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-500">From</span>
          <input type="date" value={dateFrom} onChange={e => updateFilter(setDateFrom)(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-500">To</span>
          <input type="date" value={dateTo} onChange={e => updateFilter(setDateTo)(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        {/* Action type */}
        <div className="relative">
          <select value={action} onChange={e => updateFilter(setAction)(e.target.value)}
            className="pl-3 pr-8 py-1.5 text-sm border border-gray-300 rounded-lg appearance-none
                       focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
            <option value="">All Actions</option>
            {actionTypes.map(a => (
              <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <ChevronDown size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>

        {/* User filter */}
        <div className="relative">
          <select value={userId} onChange={e => updateFilter(setUserId)(e.target.value)}
            className="pl-3 pr-8 py-1.5 text-sm border border-gray-300 rounded-lg appearance-none
                       focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
            <option value="">All Users</option>
            {users.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.username})</option>)}
          </select>
          <ChevronDown size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>

        {/* Clear filters */}
        {(dateFrom || dateTo || action || userId) && (
          <button onClick={() => {
            setDateFrom(''); setDateTo(''); setAction(''); setUserId(''); setOffset(0)
          }} className="text-xs text-blue-600 hover:underline">
            Clear filters
          </button>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-16">
          <Loader2 size={26} className="animate-spin text-gray-400" />
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4">
          <AlertCircle size={16} className="text-red-500" />
          <p className="text-red-700 text-sm">Failed to load audit log.</p>
        </div>
      )}

      {/* Empty */}
      {!isLoading && !error && logs.length === 0 && (
        <div className="flex flex-col items-center py-16 bg-white rounded-xl border border-gray-200">
          <ClipboardList size={44} className="text-gray-200 mb-4" />
          <p className="text-gray-600 font-medium">No audit entries found</p>
          <p className="text-gray-400 text-sm mt-1">Try adjusting the filters.</p>
        </div>
      )}

      {/* Table */}
      {!isLoading && logs.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-left">
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide whitespace-nowrap">Timestamp</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">User</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Action</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Entity</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {logs.map((entry, i) => (
                  <tr key={entry.id ?? i} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-500 text-xs font-mono whitespace-nowrap">
                      {entry.created_at
                        ? new Date(entry.created_at).toLocaleString('en-IN', {
                            day: '2-digit', month: 'short', year: 'numeric',
                            hour: '2-digit', minute: '2-digit', second: '2-digit',
                          })
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-gray-800 text-xs font-medium">{entry.full_name ?? '—'}</div>
                      <div className="text-gray-400 text-xs font-mono">{entry.username ?? ''}</div>
                    </td>
                    <td className="px-4 py-3"><ActionBadge action={entry.action} /></td>
                    <td className="px-4 py-3">
                      {entry.entity_type && (
                        <div className="text-xs">
                          <span className="text-gray-500">{entry.entity_type}</span>
                          {entry.entity_id && (
                            <span className="text-gray-300 font-mono ml-1.5 text-xs">{String(entry.entity_id).slice(0, 8)}…</span>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <DetailsCell details={entry.details} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 bg-gray-50">
            <span className="text-xs text-gray-500">
              Page {currentPage} · Showing {logs.length} of up to {PAGE_LIMIT} per page
            </span>
            <div className="flex items-center gap-2">
              <button onClick={() => setOffset(o => Math.max(0, o - PAGE_LIMIT))} disabled={!hasPrev}
                className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-white border border-gray-200
                           rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                <ChevronLeft size={15} />
              </button>
              <button onClick={() => setOffset(o => o + PAGE_LIMIT)} disabled={!hasNext}
                className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-white border border-gray-200
                           rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                <ChevronRight size={15} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
