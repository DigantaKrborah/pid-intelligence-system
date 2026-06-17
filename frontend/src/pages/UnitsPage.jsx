import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Building2, AlertCircle, Loader2, X, FileText } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'

// ── Add Unit Modal ────────────────────────────────────────────────────────────
// Shown when admin clicks "Add Unit". Closed by Cancel, X, or Escape key.

function AddUnitModal({ onClose, onSuccess }) {
  const [form, setForm] = useState({ unit_code: '', unit_name: '', description: '' })
  const [error, setError]   = useState('')
  const [loading, setLoading] = useState(false)

  // Allow closing with the Escape key
  React.useEffect(() => {
    function handleKey(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  function setField(field, value) {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await client.post('/api/units/', {
        unit_code:   form.unit_code.trim(),
        unit_name:   form.unit_name.trim(),
        description: form.description.trim() || null,
      })
      onSuccess()   // tell parent to refresh the units list
      onClose()
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Failed to create unit. Please try again.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    // Semi-transparent backdrop — click it to close
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">

        {/* Modal header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-gray-800 font-semibold text-base">Add Process Unit</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">

          {/* Error banner */}
          {error && (
            <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
              <AlertCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          {/* Unit Code */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
              Unit Code <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={form.unit_code}
              onChange={e => setField('unit_code', e.target.value.toUpperCase())}
              required
              maxLength={20}
              placeholder="e.g. CDU, VDU, HCU"
              className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg font-mono uppercase
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-gray-400 text-xs mt-1">
              Short code used throughout the system. Cannot be changed later.
            </p>
          </div>

          {/* Unit Name */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
              Unit Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={form.unit_name}
              onChange={e => setField('unit_name', e.target.value)}
              required
              maxLength={200}
              placeholder="e.g. Crude Distillation Unit"
              className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
              Description <span className="text-gray-400 font-normal normal-case">(optional)</span>
            </label>
            <textarea
              value={form.description}
              onChange={e => setField('description', e.target.value)}
              rows={3}
              placeholder="Brief description of this process unit…"
              className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg resize-none
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !form.unit_code.trim() || !form.unit_name.trim()}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300
                         text-white text-sm font-medium rounded-lg transition-colors
                         flex items-center gap-2"
            >
              {loading ? (
                <><Loader2 size={14} className="animate-spin" /> Creating…</>
              ) : (
                <><Plus size={14} /> Create Unit</>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}


// ── Unit card ─────────────────────────────────────────────────────────────────
// Each unit is a clickable card that navigates to the drawings list for that unit

function UnitCard({ unit }) {
  const navigate = useNavigate()

  return (
    <button
      onClick={() => navigate(`/drawings?unit_id=${unit.id}`)}
      className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm text-left w-full
                 hover:border-blue-300 hover:shadow-md transition-all duration-150 group"
    >
      {/* Header row: unit code + drawing count badge */}
      <div className="flex items-start justify-between mb-3">
        <span className="text-2xl font-bold text-slate-800 group-hover:text-blue-700 transition-colors">
          {unit.unit_code}
        </span>
        <span className="flex items-center gap-1 bg-slate-100 text-slate-600 text-xs
                         font-medium px-2.5 py-1 rounded-full">
          <FileText size={11} />
          {unit.drawing_count ?? 0} drawing{(unit.drawing_count ?? 0) !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Unit name */}
      <p className="text-gray-700 font-medium text-sm">{unit.unit_name}</p>

      {/* Description — clamped to 2 lines */}
      {unit.description && (
        <p className="text-gray-400 text-xs mt-2 line-clamp-2 leading-relaxed">
          {unit.description}
        </p>
      )}

      {/* "View drawings" hint on hover */}
      <p className="text-blue-500 text-xs mt-4 opacity-0 group-hover:opacity-100 transition-opacity">
        View drawings →
      </p>
    </button>
  )
}


// ── Units page ────────────────────────────────────────────────────────────────

export default function UnitsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)

  const isAdmin = user?.role === 'admin'

  // Fetch units list — refetched automatically after a new unit is created
  const {
    data: units = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['units'],
    queryFn:  () => client.get('/api/units/').then(r => r.data),
  })

  // Called by AddUnitModal on success to refresh the list
  function handleUnitCreated() {
    queryClient.invalidateQueries({ queryKey: ['units'] })
  }

  return (
    <div>
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Process Units</h1>
          <p className="text-gray-500 text-sm mt-1">
            Select a unit to view its P&amp;ID drawings
          </p>
        </div>

        {/* "Add Unit" button — admin only */}
        {isAdmin && (
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                       text-white text-sm font-medium rounded-lg transition-colors shadow-sm"
          >
            <Plus size={16} />
            Add Unit
          </button>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex justify-center py-16">
          <Loader2 size={28} className="animate-spin text-gray-400" />
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4">
          <AlertCircle size={18} className="text-red-500 flex-shrink-0" />
          <div>
            <p className="text-red-700 font-medium text-sm">Failed to load units</p>
            <p className="text-red-500 text-xs mt-0.5">
              {error.response?.data?.detail ?? 'Check your connection and try again.'}
            </p>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && units.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Building2 size={48} className="text-gray-300 mb-4" />
          <p className="text-gray-600 font-medium">No process units yet</p>
          <p className="text-gray-400 text-sm mt-1 max-w-xs">
            {isAdmin
              ? 'Click "Add Unit" to create your first process unit (CDU, VDU, HCU, etc.)'
              : 'No units have been configured. Ask your admin to add process units.'}
          </p>
        </div>
      )}

      {/* Units grid */}
      {!isLoading && units.length > 0 && (
        <>
          <p className="text-gray-400 text-xs mb-4">{units.length} unit{units.length !== 1 ? 's' : ''} configured</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {units.map(unit => (
              <UnitCard key={unit.id} unit={unit} />
            ))}
          </div>
        </>
      )}

      {/* Add Unit modal — rendered at root level so it overlays everything */}
      {showModal && (
        <AddUnitModal
          onClose={() => setShowModal(false)}
          onSuccess={handleUnitCreated}
        />
      )}
    </div>
  )
}
