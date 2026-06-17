import React, { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  X, Zap, Loader2, CheckCircle2, XCircle, Clock, AlertCircle,
  ChevronDown, Eye, EyeOff, Settings, ChevronRight,
} from 'lucide-react'
import client from '../api/client'

// ── Per-page status icon ──────────────────────────────────────────────────────
function PageStatusIcon({ status }) {
  if (status === 'processing') return <Loader2 size={14} className="animate-spin text-blue-500 flex-shrink-0" />
  if (status === 'completed')  return <CheckCircle2 size={14} className="text-green-500 flex-shrink-0" />
  if (status === 'failed')     return <XCircle size={14} className="text-red-500 flex-shrink-0" />
  return <Clock size={14} className="text-gray-300 flex-shrink-0" />
}

const PAGE_STATUS_LABEL = {
  pending:    'Pending',
  processing: 'Processing…',
  completed:  'Extracted',
  failed:     'Failed',
}

const PROVIDER_LABEL = { claude: 'Claude (Anthropic)', openai: 'OpenAI', gemini: 'Google Gemini' }

// ── Extraction modal ──────────────────────────────────────────────────────────
export default function ExtractionModal({ drawing, onClose, onDone }) {
  const [isRunning,   setIsRunning]   = useState(false)
  const [startError,  setStartError]  = useState('')
  const [pages,       setPages]       = useState([])
  const [tagCounts,   setTagCounts]   = useState({ equipment: 0, instruments: 0, lines: 0 })
  const [showOverride, setShowOverride] = useState(false)  // expand manual override section

  // Override fields (only used when user explicitly overrides saved settings)
  const [overrideProvider,   setOverrideProvider]   = useState('gemini')
  const [overrideModelName,  setOverrideModelName]  = useState('')
  const [overrideApiKey,     setOverrideApiKey]     = useState('')
  const [showKey,            setShowKey]            = useState(false)

  const intervalRef = useRef(null)

  // ── Load saved LLM settings ───────────────────────────────────────────────
  const { data: savedSettings, isLoading: loadingSettings } = useQuery({
    queryKey: ['llm-settings'],
    queryFn:  () => client.get('/api/settings/llm').then(r => r.data),
  })

  // ── Model catalogue (for override dropdowns) ──────────────────────────────
  const { data: modelCatalogue = {} } = useQuery({
    queryKey: ['llm-models'],
    queryFn:  () => client.get('/api/settings/llm/models').then(r => r.data),
  })

  const overrideModels = modelCatalogue[overrideProvider] || []

  // Auto-select first model when override provider changes
  useEffect(() => {
    if (overrideModels.length > 0) setOverrideModelName(overrideModels[0].id)
    else                           setOverrideModelName('')
  }, [overrideProvider, overrideModels.length])

  // ── Close on Escape ───────────────────────────────────────────────────────
  useEffect(() => {
    function handler(e) { if (e.key === 'Escape' && !isRunning) onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isRunning, onClose])

  // ── Initial page status load ──────────────────────────────────────────────
  useEffect(() => {
    client.get(`/api/extraction/status/${drawing.id}`)
      .then(({ data }) => {
        setPages(data.pages)
        setTagCounts(data.tags_extracted)
        if (data.drawing.upload_status === 'processing') setIsRunning(true)
      })
      .catch(() => {
        setPages(
          Array.from({ length: drawing.total_pages || 1 }, (_, i) => ({
            id:               `stub-${i}`,
            page_number:      i + 1,
            extraction_status: 'pending',
          }))
        )
      })
  }, [drawing.id, drawing.total_pages])

  // ── Polling while running ─────────────────────────────────────────────────
  useEffect(() => {
    if (!isRunning) { clearInterval(intervalRef.current); return }

    intervalRef.current = setInterval(async () => {
      try {
        const { data } = await client.get(`/api/extraction/status/${drawing.id}`)
        setPages(data.pages)
        setTagCounts(data.tags_extracted)

        const allTerminal = data.pages.length > 0 && data.pages.every(p =>
          p.extraction_status === 'completed' || p.extraction_status === 'failed'
        )
        if (allTerminal || data.drawing.upload_status === 'completed') {
          clearInterval(intervalRef.current)
          setIsRunning(false)
          if (onDone) onDone()
        }
      } catch { /* keep polling */ }
    }, 2000)

    return () => clearInterval(intervalRef.current)
  }, [isRunning, drawing.id, onDone])

  // ── Start extraction ──────────────────────────────────────────────────────
  async function handleStart() {
    const hasSaved  = savedSettings?.configured
    const useManual = showOverride && overrideApiKey.trim()

    // If no saved settings and no manual override → show error
    if (!hasSaved && !useManual) {
      setStartError('No LLM settings configured. Go to Settings → LLM Configuration first, or enter credentials below.')
      return
    }

    // If override panel is open but key is missing → warn
    if (showOverride && !overrideApiKey.trim()) {
      setStartError('Enter an API key or collapse the override section to use saved settings.')
      return
    }

    setStartError('')
    setIsRunning(true)

    const body = { drawing_id: drawing.id }
    if (useManual) {
      body.provider   = overrideProvider
      body.model_name = overrideModelName
      body.api_key    = overrideApiKey
    }
    // If not overriding → send no creds; backend reads from llm_settings

    try {
      await client.post('/api/extraction/start', body)
      const { data } = await client.get(`/api/extraction/status/${drawing.id}`)
      setPages(data.pages)
      setTagCounts(data.tags_extracted)
    } catch (err) {
      const msg = err.response?.data?.detail
      setStartError(typeof msg === 'string' ? msg : 'Failed to start extraction.')
      setIsRunning(false)
    }
  }

  const doneCount   = pages.filter(p => p.extraction_status === 'completed').length
  const failedCount = pages.filter(p => p.extraction_status === 'failed').length
  const hasSaved    = savedSettings?.configured

  // Button enabled when:
  //  - not running AND
  //  - either saved settings exist, or override panel has a key
  const canStart = !isRunning && (hasSaved || (showOverride && overrideApiKey.trim()))

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget && !isRunning) onClose() }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg flex flex-col max-h-[90vh]">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100 flex-shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <Zap size={16} className="text-yellow-500" />
              <h2 className="text-gray-800 font-semibold text-base">AI Tag Extraction</h2>
            </div>
            <p className="text-gray-500 text-xs font-mono">{drawing.drawing_number}</p>
            {drawing.drawing_title && (
              <p className="text-gray-400 text-xs mt-0.5 truncate max-w-xs">{drawing.drawing_title}</p>
            )}
          </div>
          <button
            onClick={onClose}
            disabled={isRunning}
            className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex-shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        {/* ── Scrollable body ──────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">

          {/* Error banner */}
          {startError && (
            <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
              <AlertCircle size={15} className="text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-red-700 text-sm">{startError}</p>
            </div>
          )}

          {/* ── LLM config section ─────────────────────────────────────── */}
          {loadingSettings ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm py-2">
              <Loader2 size={14} className="animate-spin" /> Loading settings…
            </div>
          ) : hasSaved ? (
            /* ── Saved settings banner ────────────────────────────────── */
            <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 space-y-1">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-green-600 flex-shrink-0" />
                <p className="text-green-800 text-sm font-medium">Using saved LLM settings</p>
              </div>
              <p className="text-green-700 text-xs pl-5">
                {PROVIDER_LABEL[savedSettings.provider] ?? savedSettings.provider}
                {' · '}
                {savedSettings.model_name}
                {savedSettings.api_key_hint && (
                  <span className="text-green-600"> (key ending …{savedSettings.api_key_hint})</span>
                )}
              </p>
            </div>
          ) : (
            /* ── No settings — must enter manually ───────────────────── */
            <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
              <div className="flex items-center gap-2">
                <AlertCircle size={14} className="text-amber-600 flex-shrink-0" />
                <p className="text-amber-800 text-sm font-medium">No LLM settings saved</p>
              </div>
              <p className="text-amber-700 text-xs mt-1 pl-5">
                Go to <strong>Settings → LLM Configuration</strong> to save your API key,
                or enter credentials below for this extraction only.
              </p>
            </div>
          )}

          {/* ── Override / manual entry (collapsible) ─────────────────── */}
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => setShowOverride(v => !v)}
              disabled={isRunning}
              className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-gray-600
                         hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              <div className="flex items-center gap-2">
                <Settings size={14} className="text-gray-400" />
                <span>{hasSaved ? 'Override LLM settings for this run' : 'Enter credentials manually'}</span>
              </div>
              <ChevronRight
                size={14}
                className={`text-gray-400 transition-transform ${showOverride ? 'rotate-90' : ''}`}
              />
            </button>

            {showOverride && (
              <div className="border-t border-gray-200 px-4 py-4 space-y-3 bg-gray-50/50">
                <div className="grid grid-cols-2 gap-3">
                  {/* Provider */}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                      Provider
                    </label>
                    <div className="relative">
                      <select
                        value={overrideProvider}
                        onChange={e => setOverrideProvider(e.target.value)}
                        disabled={isRunning}
                        className="w-full pl-3 pr-8 py-2 text-sm border border-gray-300 rounded-lg appearance-none
                                   focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 bg-white"
                      >
                        <option value="claude">Claude</option>
                        <option value="openai">OpenAI</option>
                        <option value="gemini">Gemini</option>
                      </select>
                      <ChevronDown size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                    </div>
                  </div>

                  {/* Model */}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                      Model
                    </label>
                    <div className="relative">
                      <select
                        value={overrideModelName}
                        onChange={e => setOverrideModelName(e.target.value)}
                        disabled={isRunning || overrideModels.length === 0}
                        className="w-full pl-3 pr-8 py-2 text-sm border border-gray-300 rounded-lg appearance-none
                                   focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 bg-white"
                      >
                        {overrideModels.map(m => (
                          <option key={m.id} value={m.id}>{m.name}</option>
                        ))}
                      </select>
                      <ChevronDown size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                    </div>
                  </div>
                </div>

                {/* API key */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                    API Key {!hasSaved && <span className="text-red-400">*</span>}
                  </label>
                  <div className="relative">
                    <input
                      type={showKey ? 'text' : 'password'}
                      value={overrideApiKey}
                      onChange={e => setOverrideApiKey(e.target.value)}
                      disabled={isRunning}
                      placeholder={hasSaved ? 'Leave blank to use saved key' : 'Paste your API key'}
                      className="w-full px-3 pr-10 py-2 text-sm border border-gray-300 rounded-lg font-mono
                                 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 bg-white"
                    />
                    <button
                      type="button"
                      onClick={() => setShowKey(v => !v)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                  {hasSaved && (
                    <p className="text-xs text-gray-400 mt-1">
                      Leave blank to use the API key from Settings.
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* ── Per-page progress ───────────────────────────────────────── */}
          {pages.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-600 uppercase tracking-wide mb-2">
                Pages ({doneCount}/{pages.length} extracted
                {failedCount > 0 ? `, ${failedCount} failed` : ''})
              </p>
              <div className="rounded-lg border border-gray-200 overflow-hidden">
                {pages.map((page, idx) => (
                  <div
                    key={page.id}
                    className={`flex items-center gap-3 px-3 py-2 text-sm
                      ${idx < pages.length - 1 ? 'border-b border-gray-100' : ''}
                      ${page.extraction_status === 'completed'  ? 'bg-green-50/50'  : ''}
                      ${page.extraction_status === 'failed'     ? 'bg-red-50/50'    : ''}
                      ${page.extraction_status === 'processing' ? 'bg-blue-50/50'   : ''}
                    `}
                  >
                    <PageStatusIcon status={page.extraction_status} />
                    <span className="text-gray-700">Page {page.page_number}</span>
                    <span className="ml-auto text-xs text-gray-400">
                      {PAGE_STATUS_LABEL[page.extraction_status] ?? page.extraction_status}
                    </span>
                    {page.extracted_at && (
                      <span className="text-xs text-gray-300 hidden sm:inline">
                        {new Date(page.extracted_at).toLocaleTimeString('en-IN', {
                          hour: '2-digit', minute: '2-digit',
                        })}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Tag count summary ────────────────────────────────────────── */}
          {(tagCounts.equipment > 0 || tagCounts.instruments > 0 || tagCounts.lines > 0) && (
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Equipment',   count: tagCounts.equipment,   cls: 'text-blue-700 bg-blue-50'     },
                { label: 'Instruments', count: tagCounts.instruments, cls: 'text-purple-700 bg-purple-50' },
                { label: 'Lines',       count: tagCounts.lines,       cls: 'text-emerald-700 bg-emerald-50' },
              ].map(({ label, count, cls }) => (
                <div key={label} className={`rounded-lg px-3 py-2.5 text-center ${cls}`}>
                  <p className="text-xl font-bold">{count}</p>
                  <p className="text-xs font-medium opacity-80">{label}</p>
                </div>
              ))}
            </div>
          )}

        </div>

        {/* ── Footer ──────────────────────────────────────────────────── */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between flex-shrink-0">
          <button
            onClick={onClose}
            disabled={isRunning}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors disabled:opacity-30"
          >
            {isRunning ? 'Running in background…' : 'Close'}
          </button>
          <button
            onClick={handleStart}
            disabled={!canStart}
            className="flex items-center gap-2 px-5 py-2 bg-yellow-500 hover:bg-yellow-600
                       disabled:bg-gray-200 disabled:text-gray-400
                       text-white text-sm font-medium rounded-lg transition-colors"
          >
            {isRunning ? (
              <><Loader2 size={14} className="animate-spin" /> Extracting…</>
            ) : doneCount > 0 ? (
              <><Zap size={14} /> Re-extract</>
            ) : (
              <><Zap size={14} /> Start Extraction</>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
