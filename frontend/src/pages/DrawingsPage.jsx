import React, { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Upload, Eye, Zap, Trash2, AlertCircle, Loader2,
  FileText, ChevronDown, CheckCircle2, Clock, AlertTriangle,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import UploadDrawingModal from '../components/UploadDrawingModal'
import ExtractionModal from '../components/ExtractionModal'

// ── Status badge ──────────────────────────────────────────────────────────────
// Shows upload/extraction status for each drawing row

function StatusBadge({ drawing }) {
  const status = drawing.upload_status

  const STYLE = {
    uploaded:   'bg-gray-100 text-gray-600',
    processing: 'bg-yellow-100 text-yellow-700',
    completed:  'bg-green-100 text-green-700',
    failed:     'bg-red-100 text-red-700',
  }

  // For completed/failed drawings also show extracted page count
  let label = status.charAt(0).toUpperCase() + status.slice(1)
  const ICON = {
    uploaded:   <Clock size={11} className="inline mr-1" />,
    processing: <Loader2 size={11} className="inline mr-1 animate-spin" />,
    completed:  <CheckCircle2 size={11} className="inline mr-1" />,
    failed:     <AlertTriangle size={11} className="inline mr-1" />,
  }

  const showPages = (status === 'completed' || status === 'failed') && drawing.total_pages > 0
  const pagesLabel = showPages
    ? ` (${drawing.pages_extracted ?? 0}/${drawing.total_pages} pages)`
    : ''

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STYLE[status] ?? STYLE.uploaded}`}>
      {ICON[status]}
      {label}{pagesLabel}
    </span>
  )
}

// ── Delete confirm dialog ─────────────────────────────────────────────────────
// Inline modal that asks "Are you sure?" before deleting

function DeleteConfirmDialog({ drawing, onCancel, onConfirm, loading }) {
  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onCancel() }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
            <Trash2 size={18} className="text-red-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 text-sm">Delete Drawing</h3>
            <p className="text-gray-500 text-xs mt-0.5">This action cannot be undone</p>
          </div>
        </div>
        <p className="text-gray-600 text-sm mb-6">
          Delete <strong className="font-mono">{drawing.drawing_number}</strong>?
          This will permanently remove the drawing file, all page images, and all extracted tags.
        </p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-300
                       text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
            {loading ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}


// ── Drawings page ─────────────────────────────────────────────────────────────

export default function DrawingsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // unit_id comes from URL: /drawings?unit_id=...
  // (UnitsPage navigates here with this param already set)
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedUnitId = searchParams.get('unit_id') || ''

  const [showUpload, setShowUpload]           = useState(false)
  const [extractionTarget, setExtractionTarget] = useState(null)  // drawing object → open modal
  const [deleteTarget, setDeleteTarget]         = useState(null)  // drawing object → confirm dialog
  const [deleteLoading, setDeleteLoading]       = useState(false)
  const [deleteError, setDeleteError]           = useState('')

  const isAdmin = user?.role === 'admin'

  // ── Units for filter dropdown ──────────────────────────────────────────────
  const { data: units = [] } = useQuery({
    queryKey: ['units'],
    queryFn:  () => client.get('/api/units/').then(r => r.data),
  })

  // ── Drawings list, filtered by selected unit ───────────────────────────────
  const {
    data: drawings = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['drawings', selectedUnitId],
    queryFn: () => {
      const url = selectedUnitId
        ? `/api/drawings/?unit_id=${selectedUnitId}`
        : '/api/drawings/'
      return client.get(url).then(r => r.data)
    },
  })

  // ── Change the unit filter → update the URL param ─────────────────────────
  function handleUnitChange(val) {
    if (val) setSearchParams({ unit_id: val })
    else     setSearchParams({})
  }

  // ── Delete a drawing ───────────────────────────────────────────────────────
  async function handleDelete() {
    if (!deleteTarget) return
    setDeleteLoading(true)
    setDeleteError('')
    try {
      await client.delete(`/api/drawings/${deleteTarget.id}`)
      // Invalidate both the full list and the unit-filtered list
      queryClient.invalidateQueries({ queryKey: ['drawings'] })
      setDeleteTarget(null)
    } catch (err) {
      setDeleteError(err.response?.data?.detail ?? 'Delete failed. Please try again.')
    } finally {
      setDeleteLoading(false)
    }
  }

  // ── After successful upload → refresh table ────────────────────────────────
  function handleUploadSuccess() {
    queryClient.invalidateQueries({ queryKey: ['drawings'] })
  }

  // ── After extraction finishes → refresh table ─────────────────────────────
  function handleExtractionDone() {
    queryClient.invalidateQueries({ queryKey: ['drawings'] })
    setExtractionTarget(null)
  }

  return (
    <div>
      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">P&amp;ID Drawings</h1>
          <p className="text-gray-500 text-sm mt-1">
            {drawings.length} drawing{drawings.length !== 1 ? 's' : ''}
            {selectedUnitId && units.length > 0 && (() => {
              const u = units.find(x => x.id === selectedUnitId)
              return u ? ` in ${u.unit_code} — ${u.unit_name}` : ''
            })()}
          </p>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                     text-white text-sm font-medium rounded-lg transition-colors shadow-sm"
        >
          <Upload size={16} />
          Upload P&amp;ID
        </button>
      </div>

      {/* ── Filter bar ───────────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm px-4 py-3 mb-4 flex items-center gap-3">
        <span className="text-gray-500 text-sm flex-shrink-0">Filter by unit:</span>
        <div className="relative">
          <select
            value={selectedUnitId}
            onChange={e => handleUnitChange(e.target.value)}
            className="pl-3 pr-8 py-1.5 text-sm border border-gray-300 rounded-lg appearance-none
                       focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">All units</option>
            {units.map(u => (
              <option key={u.id} value={u.id}>
                {u.unit_code} — {u.unit_name}
              </option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>
        {selectedUnitId && (
          <button
            onClick={() => handleUnitChange('')}
            className="text-xs text-blue-600 hover:underline"
          >
            Clear filter
          </button>
        )}
      </div>

      {/* ── Loading state ────────────────────────────────────────────────── */}
      {isLoading && (
        <div className="flex justify-center py-16">
          <Loader2 size={28} className="animate-spin text-gray-400" />
        </div>
      )}

      {/* ── Error state ──────────────────────────────────────────────────── */}
      {error && !isLoading && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4">
          <AlertCircle size={18} className="text-red-500 flex-shrink-0" />
          <p className="text-red-700 text-sm">
            {error.response?.data?.detail ?? 'Failed to load drawings.'}
          </p>
        </div>
      )}

      {/* ── Empty state ──────────────────────────────────────────────────── */}
      {!isLoading && !error && drawings.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center bg-white rounded-xl border border-gray-200">
          <FileText size={48} className="text-gray-300 mb-4" />
          <p className="text-gray-600 font-medium">No drawings yet</p>
          <p className="text-gray-400 text-sm mt-1 max-w-xs">
            Click <strong>Upload P&amp;ID</strong> to add the first drawing.
          </p>
        </div>
      )}

      {/* ── Drawings table ───────────────────────────────────────────────── */}
      {!isLoading && drawings.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {deleteError && (
            <div className="bg-red-50 border-b border-red-200 px-4 py-2 flex items-center gap-2">
              <AlertCircle size={14} className="text-red-500" />
              <span className="text-red-600 text-xs">{deleteError}</span>
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-left">
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Unit</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Drawing No.</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Title</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide w-16 text-center">Rev</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide w-14 text-center">Pages</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Uploaded</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {drawings.map(d => (
                  <tr key={d.id} className="hover:bg-gray-50 transition-colors">

                    {/* Unit code */}
                    <td className="px-4 py-3">
                      <span className="bg-slate-100 text-slate-700 text-xs font-semibold px-2 py-0.5 rounded">
                        {d.unit_code}
                      </span>
                    </td>

                    {/* Drawing number — monospace */}
                    <td className="px-4 py-3 font-mono text-xs text-gray-800 whitespace-nowrap">
                      {d.drawing_number}
                    </td>

                    {/* Title — truncate if long */}
                    <td className="px-4 py-3 text-gray-600 max-w-xs">
                      <span className="block truncate">{d.drawing_title ?? '—'}</span>
                    </td>

                    {/* Revision */}
                    <td className="px-4 py-3 text-gray-500 text-xs text-center font-mono">
                      {d.revision ?? '—'}
                    </td>

                    {/* Page count */}
                    <td className="px-4 py-3 text-gray-600 text-center">{d.total_pages ?? '—'}</td>

                    {/* Extraction status */}
                    <td className="px-4 py-3">
                      <StatusBadge drawing={d} />
                    </td>

                    {/* Upload date */}
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {new Date(d.uploaded_at).toLocaleDateString('en-IN', {
                        day: '2-digit', month: 'short', year: 'numeric',
                      })}
                    </td>

                    {/* Action buttons */}
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">

                        {/* View detail */}
                        <button
                          onClick={() => navigate(`/drawings/${d.id}`)}
                          title="View details"
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50
                                     rounded-lg transition-colors"
                        >
                          <Eye size={15} />
                        </button>

                        {/* Start / view extraction — disabled if file conversion failed */}
                        <button
                          onClick={() => setExtractionTarget(d)}
                          disabled={d.upload_status === 'failed'}
                          title={d.upload_status === 'failed' ? 'File could not be processed' : 'Run AI extraction'}
                          className="p-1.5 text-gray-400 hover:text-yellow-600 hover:bg-yellow-50
                                     rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <Zap size={15} />
                        </button>

                        {/* Delete — admin only */}
                        {isAdmin && (
                          <button
                            onClick={() => { setDeleteError(''); setDeleteTarget(d) }}
                            title="Delete drawing"
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50
                                       rounded-lg transition-colors"
                          >
                            <Trash2 size={15} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Modals ───────────────────────────────────────────────────────── */}

      {showUpload && (
        <UploadDrawingModal
          onClose={() => setShowUpload(false)}
          onSuccess={handleUploadSuccess}
          defaultUnitId={selectedUnitId}
        />
      )}

      {extractionTarget && (
        <ExtractionModal
          drawing={extractionTarget}
          onClose={() => setExtractionTarget(null)}
          onDone={handleExtractionDone}
        />
      )}

      {deleteTarget && (
        <DeleteConfirmDialog
          drawing={deleteTarget}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
          loading={deleteLoading}
        />
      )}
    </div>
  )
}
