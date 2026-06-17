import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search, Loader2, AlertCircle, ChevronDown,
  Tag, Wrench, Activity, GitBranch, ArrowRight,
  ArrowUpRight, ArrowDownRight,
} from 'lucide-react'
import client from '../api/client'

// ── Category badge ────────────────────────────────────────────────────────────
const CATEGORY_CONFIG = {
  EQUIPMENT:  { cls: 'bg-blue-50 text-blue-700',       label: 'Equipment',  Icon: Wrench    },
  INSTRUMENT: { cls: 'bg-purple-50 text-purple-700',   label: 'Instrument', Icon: Activity  },
  LINE:       { cls: 'bg-emerald-50 text-emerald-700', label: 'Line Spec',  Icon: GitBranch },
}

function CategoryBadge({ category }) {
  const cfg = CATEGORY_CONFIG[category] ?? { cls: 'bg-gray-100 text-gray-600', label: category }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  )
}

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

// Small chips showing up/downstream tag numbers (max 3 visible, then "+N")
function ConnectivityChips({ tags, direction }) {
  if (!tags || tags.length === 0) return <span className="text-gray-300 text-xs">—</span>

  const isUp     = direction === 'up'
  const colorCls = isUp ? 'bg-blue-50 text-blue-600' : 'bg-amber-50 text-amber-700'
  const Icon     = isUp ? ArrowUpRight : ArrowDownRight
  const visible  = tags.slice(0, 3)
  const extra    = tags.length - 3

  return (
    <div className="flex flex-wrap gap-1 items-center">
      {visible.map(t => (
        <span key={t} className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-mono font-medium ${colorCls}`}>
          <Icon size={10} />
          {t}
        </span>
      ))}
      {extra > 0 && (
        <span className="text-xs text-gray-400">+{extra}</span>
      )}
    </div>
  )
}

// ── Tag Search page ───────────────────────────────────────────────────────────
export default function TagSearchPage() {
  const navigate = useNavigate()

  const [inputValue,    setInputValue]    = useState('')
  const [debouncedQ,    setDebouncedQ]    = useState('')
  const [selectedUnit,  setSelectedUnit]  = useState('')
  const [tagType,       setTagType]       = useState('')

  // 400 ms debounce on the search box
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(inputValue.trim()), 400)
    return () => clearTimeout(timer)
  }, [inputValue])

  // Units dropdown
  const { data: units = [] } = useQuery({
    queryKey: ['units'],
    queryFn:  () => client.get('/api/units/').then(r => r.data),
  })

  // Fire when:
  //   - a unit is selected (show all tags for that unit), OR
  //   - the user has typed ≥ 2 characters
  const queryEnabled = !!selectedUnit || debouncedQ.length >= 2

  const {
    data:      results = [],
    isLoading: searching,
    error,
  } = useQuery({
    queryKey: ['tagSearch', debouncedQ, selectedUnit, tagType],
    queryFn: () => {
      const params = new URLSearchParams()
      if (debouncedQ)    params.set('q', debouncedQ)
      if (selectedUnit)  params.set('unit_id', selectedUnit)
      if (tagType)       params.set('tag_type', tagType)
      return client.get(`/api/tags/search?${params}`).then(r => r.data)
    },
    enabled: queryEnabled,
  })

  const browsingAll = queryEnabled && !debouncedQ   // unit selected, no text typed
  const hasResults  = results.length > 0
  const unitLabel   = selectedUnit
    ? (units.find(u => u.id === selectedUnit)?.unit_code ?? '')
    : ''

  return (
    <div className="max-w-6xl mx-auto">

      {/* ── Hero search bar ────────────────────────────────────────────── */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-2 mb-1">
          <Tag size={22} className="text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">Tag Search</h1>
        </div>
        <p className="text-gray-500 text-sm">
          Select a unit to browse all tags, or type a tag number / description to search
        </p>

        <div className="relative mt-5 max-w-2xl mx-auto">
          <Search size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          <input
            autoFocus
            type="text"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder="e.g.  04-VV-002,  E-101,  TIC-2201,  charge pump…"
            className="w-full pl-12 pr-12 py-3.5 text-sm border border-gray-300 rounded-2xl shadow-sm
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
          />
          {searching && (
            <Loader2 size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-blue-500 animate-spin" />
          )}
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

        {/* Result count */}
        {queryEnabled && !searching && (
          <span className="ml-auto text-xs text-gray-400">
            {hasResults
              ? `${results.length} tag${results.length !== 1 ? 's' : ''}${results.length >= 200 ? ' (showing first 200)' : ''}`
              : 'No tags found'}
          </span>
        )}
      </div>

      {/* ── Error ────────────────────────────────────────────────────────── */}
      {error && !searching && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4 mb-4">
          <AlertCircle size={16} className="text-red-500 flex-shrink-0" />
          <p className="text-red-700 text-sm">Search failed. Please try again.</p>
        </div>
      )}

      {/* ── Empty prompt — no unit selected, no query ────────────────────── */}
      {!queryEnabled && !searching && (
        <div className="text-center py-16">
          <Tag size={48} className="text-gray-200 mx-auto mb-4" />
          <p className="text-gray-400 text-sm font-medium">Select a unit or type to search</p>
          <p className="text-gray-300 text-xs mt-1">
            Selecting a unit shows all extracted tags for that unit
          </p>
        </div>
      )}

      {/* ── No results after a query ─────────────────────────────────────── */}
      {queryEnabled && !searching && !error && results.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Tag size={40} className="text-gray-200 mx-auto mb-3" />
          <p className="text-gray-600 font-medium text-sm">No tags found</p>
          <p className="text-gray-400 text-sm mt-1">
            {debouncedQ
              ? <>No results for <strong>"{debouncedQ}"</strong>{unitLabel ? ` in ${unitLabel}` : ''}</>
              : <>No extracted tags yet for <strong>{unitLabel}</strong>. Run AI extraction on the drawings first.</>
            }
          </p>
        </div>
      )}

      {/* ── Results table ─────────────────────────────────────────────────── */}
      {hasResults && !error && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {browsingAll && unitLabel && (
            <div className="px-4 py-2.5 bg-blue-50 border-b border-blue-100 text-xs text-blue-700 font-medium">
              All extracted tags for unit <strong>{unitLabel}</strong>
              {tagType && ` · ${tagType}`}
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-left">
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Tag Number</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Category</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Type</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Description</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Drawing</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                    <span className="flex items-center gap-1">
                      <ArrowUpRight size={12} className="text-blue-500" /> Upstream
                    </span>
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                    <span className="flex items-center gap-1">
                      <ArrowDownRight size={12} className="text-amber-500" /> Downstream
                    </span>
                  </th>
                  <th className="w-8" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {results.map((r, idx) => (
                  <tr
                    key={`${r.tag_number}-${idx}`}
                    onClick={() => navigate(`/tags/${encodeURIComponent(r.tag_number)}${selectedUnit ? `?unit_id=${selectedUnit}` : ''}`)}
                    className="hover:bg-blue-50/60 cursor-pointer transition-colors group"
                  >
                    {/* Tag number */}
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs font-bold text-gray-900 whitespace-nowrap">
                        {r.tag_number}
                      </span>
                      {!selectedUnit && (
                        <span className="ml-2 bg-slate-100 text-slate-600 text-xs px-1.5 py-0.5 rounded font-medium">
                          {r.unit_code}
                        </span>
                      )}
                    </td>

                    {/* Category */}
                    <td className="px-4 py-3">
                      <CategoryBadge category={r.tag_category} />
                    </td>

                    {/* Tag type */}
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">{r.tag_type || '—'}</td>

                    {/* Description */}
                    <td className="px-4 py-3 text-gray-600 max-w-xs">
                      <span className="block truncate">{r.description || '—'}</span>
                    </td>

                    {/* Drawing */}
                    <td className="px-4 py-3 font-mono text-xs text-gray-500 whitespace-nowrap">
                      {r.drawing_number}
                      <span className="ml-1 text-gray-300">p{r.page_number}</span>
                    </td>

                    {/* Upstream tags */}
                    <td className="px-4 py-3">
                      <ConnectivityChips tags={r.upstream_tags} direction="up" />
                    </td>

                    {/* Downstream tags */}
                    <td className="px-4 py-3">
                      <ConnectivityChips tags={r.downstream_tags} direction="down" />
                    </td>

                    {/* Arrow */}
                    <td className="px-3 py-3 text-gray-300 group-hover:text-blue-500 transition-colors">
                      <ArrowRight size={14} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="px-4 py-2.5 border-t border-gray-100 bg-gray-50 text-right">
            <span className="text-xs text-gray-400">
              {results.length} result{results.length !== 1 ? 's' : ''}
              {results.length >= 200 ? ' — showing first 200, use search to narrow down' : ''}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
