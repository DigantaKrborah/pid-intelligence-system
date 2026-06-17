import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search, Loader2, AlertCircle, ChevronDown,
  Tag, Wrench, Activity, GitBranch, ArrowRight,
} from 'lucide-react'
import client from '../api/client'

// ── Category badge colour map ─────────────────────────────────────────────────
const CATEGORY_CONFIG = {
  EQUIPMENT:  { cls: 'bg-blue-50 text-blue-700',     label: 'Equipment',   Icon: Wrench    },
  INSTRUMENT: { cls: 'bg-purple-50 text-purple-700', label: 'Instrument',  Icon: Activity  },
  LINE:       { cls: 'bg-emerald-50 text-emerald-700', label: 'Line Spec', Icon: GitBranch },
}

function CategoryBadge({ category }) {
  const cfg = CATEGORY_CONFIG[category] ?? { cls: 'bg-gray-100 text-gray-600', label: category }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  )
}

// Pill-style toggle button (used for the tag-type filter row)
function PillButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-sm rounded-lg transition-colors border
        ${active
          ? 'bg-blue-600 text-white border-blue-600'
          : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50 hover:border-gray-400'
        }`}
    >
      {children}
    </button>
  )
}

// ── Tag Search page ───────────────────────────────────────────────────────────
export default function TagSearchPage() {
  const navigate = useNavigate()

  // Live input value (changes on every keystroke)
  const [inputValue, setInputValue]     = useState('')
  // Debounced value — updated 400 ms after typing stops
  const [debouncedQ, setDebouncedQ]     = useState('')
  const [selectedUnit, setSelectedUnit] = useState('')
  // '' | 'equipment' | 'instrument' | 'line'  — must match backend query param values
  const [tagType, setTagType]           = useState('')

  // ── 400 ms debounce ────────────────────────────────────────────────────────
  // Avoids calling the API on every single keystroke — waits for the user to pause.
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(inputValue.trim()), 400)
    return () => clearTimeout(timer)  // cancel if the user types again before timeout fires
  }, [inputValue])

  // ── Units for the filter dropdown ──────────────────────────────────────────
  const { data: units = [] } = useQuery({
    queryKey: ['units'],
    queryFn:  () => client.get('/api/units/').then(r => r.data),
  })

  // ── Search results ─────────────────────────────────────────────────────────
  // Only fires when query is ≥ 2 characters — avoids huge result sets.
  const {
    data:      results = [],
    isLoading: searching,
    error,
  } = useQuery({
    queryKey: ['tagSearch', debouncedQ, selectedUnit, tagType],
    queryFn: () => {
      const params = new URLSearchParams({ q: debouncedQ })
      if (selectedUnit) params.set('unit_id', selectedUnit)
      if (tagType)      params.set('tag_type', tagType)
      return client.get(`/api/tags/search?${params}`).then(r => r.data)
    },
    enabled: debouncedQ.length >= 2,
  })

  const hasQuery   = debouncedQ.length >= 2
  const hasResults = results.length > 0

  return (
    <div className="max-w-5xl mx-auto">

      {/* ── Hero search bar ────────────────────────────────────────────── */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-2 mb-1">
          <Tag size={22} className="text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">Tag Search</h1>
        </div>
        <p className="text-gray-500 text-sm">
          Search equipment, instruments, and lines by tag number, description, or service
        </p>

        {/* Search input — autoFocus so it's ready to type straight away */}
        <div className="relative mt-5 max-w-2xl mx-auto">
          <Search size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          <input
            autoFocus
            type="text"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder="e.g.  E-101,  TIC-2201,  crude,  overhead condenser…"
            className="w-full pl-12 pr-12 py-3.5 text-sm border border-gray-300 rounded-2xl shadow-sm
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
          />
          {/* Spinner shows while the API call is in flight */}
          {searching && (
            <Loader2 size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-blue-500 animate-spin" />
          )}
          {/* Clear button */}
          {inputValue && !searching && (
            <button
              onClick={() => { setInputValue(''); setDebouncedQ('') }}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-300 hover:text-gray-500 text-lg leading-none"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* ── Filter bar ───────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2 mb-5 bg-white rounded-xl border border-gray-200 shadow-sm px-4 py-3">

        {/* Unit filter */}
        <div className="relative">
          <select
            value={selectedUnit}
            onChange={e => setSelectedUnit(e.target.value)}
            className="pl-3 pr-8 py-1.5 text-sm border border-gray-300 rounded-lg appearance-none
                       focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">All Units</option>
            {units.map(u => (
              <option key={u.id} value={u.id}>{u.unit_code} — {u.unit_name}</option>
            ))}
          </select>
          <ChevronDown size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>

        {/* Tag type filter pills */}
        <div className="flex items-center gap-1.5">
          {[
            { val: '',           label: 'All Types' },
            { val: 'equipment',  label: 'Equipment' },
            { val: 'instrument', label: 'Instrument' },
            { val: 'line',       label: 'Line' },
          ].map(opt => (
            <PillButton key={opt.val} active={tagType === opt.val} onClick={() => setTagType(opt.val)}>
              {opt.label}
            </PillButton>
          ))}
        </div>

        {/* Result count — shown once we have a result set */}
        {hasQuery && !searching && (
          <span className="ml-auto text-xs text-gray-400">
            {hasResults
              ? `${results.length} result${results.length !== 1 ? 's' : ''}`
              : 'No results'}
          </span>
        )}
      </div>

      {/* ── States ───────────────────────────────────────────────────────── */}

      {/* Error */}
      {error && !searching && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4 mb-4">
          <AlertCircle size={16} className="text-red-500 flex-shrink-0" />
          <p className="text-red-700 text-sm">Search failed. Please try again.</p>
        </div>
      )}

      {/* Prompt: no query entered yet */}
      {!hasQuery && !searching && (
        <div className="text-center py-16">
          <Search size={48} className="text-gray-200 mx-auto mb-4" />
          <p className="text-gray-400 text-sm">Type at least 2 characters to search</p>
        </div>
      )}

      {/* No results */}
      {hasQuery && !searching && !error && results.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Tag size={40} className="text-gray-200 mx-auto mb-3" />
          <p className="text-gray-600 font-medium text-sm">No tags found</p>
          <p className="text-gray-400 text-sm mt-1">
            No results for&nbsp;
            <strong>"{debouncedQ}"</strong>
            {tagType ? ` in ${tagType} tags` : ''}
            {selectedUnit && units.find(u => u.id === selectedUnit)
              ? ` in unit ${units.find(u => u.id === selectedUnit)?.unit_code}`
              : ''}
          </p>
        </div>
      )}

      {/* ── Results table ─────────────────────────────────────────────── */}
      {hasResults && !error && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-left">
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Tag Number</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Category</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Type</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Description</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Unit</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Drawing</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide text-center w-14">Page</th>
                  <th className="w-8" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {results.map((r, idx) => (
                  <tr
                    key={`${r.tag_number}-${idx}`}
                    onClick={() => navigate(`/tags/${encodeURIComponent(r.tag_number)}`)}
                    className="hover:bg-blue-50/60 cursor-pointer transition-colors group"
                  >
                    {/* Tag number — bold monospace */}
                    <td className="px-4 py-3 font-mono text-xs font-bold text-gray-900 whitespace-nowrap">
                      {r.tag_number}
                    </td>

                    {/* Category badge (Equipment / Instrument / Line) */}
                    <td className="px-4 py-3">
                      <CategoryBadge category={r.tag_category} />
                    </td>

                    {/* Tag type (e.g. HEAT EXCHANGER, PRESSURE TRANSMITTER) */}
                    <td className="px-4 py-3 text-gray-500 text-xs">{r.tag_type || '—'}</td>

                    {/* Description — truncated */}
                    <td className="px-4 py-3 text-gray-600 max-w-xs">
                      <span className="block truncate">{r.description || '—'}</span>
                    </td>

                    {/* Unit code badge */}
                    <td className="px-4 py-3">
                      <span className="bg-slate-100 text-slate-700 text-xs font-semibold px-2 py-0.5 rounded">
                        {r.unit_code}
                      </span>
                    </td>

                    {/* Drawing number */}
                    <td className="px-4 py-3 font-mono text-xs text-gray-500 whitespace-nowrap">
                      {r.drawing_number}
                    </td>

                    {/* Page number */}
                    <td className="px-4 py-3 text-gray-500 text-xs text-center">{r.page_number}</td>

                    {/* Arrow hint — appears on hover */}
                    <td className="px-3 py-3 text-gray-300 group-hover:text-blue-500 transition-colors">
                      <ArrowRight size={14} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Footer: total count */}
          <div className="px-4 py-2.5 border-t border-gray-100 bg-gray-50 text-right">
            <span className="text-xs text-gray-400">
              {results.length} result{results.length !== 1 ? 's' : ''}
              {results.length === 100 ? ' — showing first 100, narrow your search for more' : ''}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
