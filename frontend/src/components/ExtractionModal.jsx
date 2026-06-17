import React, { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  X, Zap, Loader2, CheckCircle2, XCircle, Clock, AlertCircle,
  ChevronDown, Eye, EyeOff, Info,
} from 'lucide-react'
import client from '../api/client'

// ── Per-page status icon ──────────────────────────────────────────────────────
function PageStatusIcon({ status }) {
  if (status === 'processing') return <Loader2 size={14} className="animate-spin text-blue-500 flex-shrink-0" />
  if (status === 'completed')  return <CheckCircle2 size={14} className="text-green-500 flex-shrink-0" />
  if (status === 'failed')     return <XCircle size={14} className="text-red-500 flex-shrink-0" />
  return <Clock size={14} className="text-gray-300 flex-shrink-0" />
}

// ── Page status label text ────────────────────────────────────────────────────
const PAGE_STATUS_LABEL = {
  pending:    'Pending',
  processing: 'Processing…',
  completed:  'Extracted',
  failed:     'Failed',
}

// ── Extraction modal ──────────────────────────────────────────────────────────
// Props:
//   drawing  — the drawing row from the list endpoint
//              { id, drawing_number, drawing_title, total_pages, upload_status }
//   onClose  — called when user closes the modal (extraction may still be running)
//   onDone   — called when extraction finishes (all pages completed or failed)

export default function ExtractionModal({ drawing, onClose, onDone }) {
  const [provider, setProvider]   = useState('claude')
  const [modelName, setModelName] = useState('')
  const [apiKey, setApiKey]       = useState('')
  const [showKey, setShowKey]     = useState(false)   // toggle password visibility
  const [isRunning, setIsRunning] = useState(false)
  const [startError, setStartError] = useState('')

  // Per-page status comes from polling the extraction status endpoint
  const [pages, setPages]         = useState([])
  const [tagCounts, setTagCounts] = useState({ equipment: 0, instruments: 0, lines: 0 })

  const intervalRef = useRef(null)

  // Close on Escape (only if not running)
  useEffect(() => {
    function handler(e) { if (e.key === 'Escape' && !isRunning) onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isRunning, onClose])

  // ── Model catalogue ────────────────────────────────────────────────────────
  const { data: modelCatalogue = {} } = useQuery({
    queryKey: ['llm-models'],
    queryFn:  () => client.get('/api/settings/llm/models').then(r => r.data),
  })

  const availableModels = modelCatalogue[provider] || []

  // Auto-select first model when provider changes
  useEffect(() => {
    if (availableModels.length > 0) setModelName(availableModels[0].id)
    else                            setModelName('')
  }, [provider, availableModels.length])

  // ── Initial page status load ───────────────────────────────────────────────
  // On open, fetch current extraction status so we show real per-page state
  // (may already be partially extracted from a previous session)
  useEffect(() => {
    client.get(`/api/extraction/status/${drawing.id}`)
      .then(({ data }) => {
        setPages(data.pages)
        setTagCounts(data.tags_extracted)
        // If extraction is already running (from another session), start polling
        if (data.drawing.upload_status === 'processing') {
          setIsRunning(true)
        }
      })
      .catch(() => {
        // If status fails (e.g. no pages yet), initialise with empty page stubs
        // based on total_pages from the drawing list row
        setPages(
          Array.from({ length: drawing.total_pages || 1 }, (_, i) => ({
            id:               `stub-${i}`,
            page_number:      i + 1,
            extraction_status: 'pending',
          }))
        )
      })
  }, [drawing.id, drawing.total_pages])

  // ── Polling ────────────────────────────────────────────────────────────────
  // While isRunning: poll /api/extraction/status every 2 seconds and
  // update per-page status + tag counts in state.
  useEffect(() => {
    if (!isRunning) {
      clearInterval(intervalRef.current)
      return
    }

    intervalRef.current = setInterval(async () => {
      try {
        const { data } = await client.get(`/api/extraction/status/${drawing.id}`)
        setPages(data.pages)
        setTagCounts(data.tags_extracted)

        // Stop when every page is in a terminal state (not pending/processing)
        const allTerminal = data.pages.length > 0 && data.pages.every(p =>
          p.extraction_status === 'completed' || p.extraction_status === 'failed'
        )
        if (allTerminal || data.drawing.upload_status === 'completed') {
          clearInterval(intervalRef.current)
          setIsRunning(false)
          if (onDone) onDone()
        }
      } catch {
        // Ignore poll errors — keep trying
      }
    }, 2000)

    // Cleanup: clear the interval if this effect re-runs or the modal unmounts
    return () => clearInterval(intervalRef.current)
  }, [isRunning, drawing.id, onDone])

  // ── Start extraction ───────────────────────────────────────────────────────
  async function handleStart() {
    if (!apiKey.trim()) { setStartError('Please enter your API key.'); return }
    if (!modelName)     { setStartError('Please select a model.'); return }

    setStartError('')
    setIsRunning(true)

    try {
      await client.post('/api/extraction/start', {
        drawing_id: drawing.id,
        provider,
        model_name: modelName,
        api_key:    apiKey,
      })
      // Immediately fetch status so the page list shows 'processing' for the first page
      const { data } = await client.get(`/api/extraction/status/${drawing.id}`)
      setPages(data.pages)
      setTagCounts(data.tags_extracted)
    } catch (err) {
      const msg = err.response?.data?.detail
      setStartError(typeof msg === 'string' ? msg : 'Failed to start extraction. Check your API key.')
      setIsRunning(false)
    }
  }

  // ── Derived counters ───────────────────────────────────────────────────────
  const doneCount   = pages.filter(p => p.extraction_status === 'completed').length
  const failedCount = pages.filter(p => p.extraction_status === 'failed').length

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
        <div className="flex-1 overflow-y-auto p-6 space-y-5">

          {/* Start error */}
          {startError && (
            <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
              <AlertCircle size={15} className="text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-red-700 text-sm">{startError}</p>
            </div>
          )}

          {/* ── LLM provider ───────────────────────────────────────────── */}
          <div className="grid grid-cols-2 gap-3">
            {/* Provider */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                Provider
              </label>
              <div className="relative">
                <select
                  value={provider}
                  onChange={e => setProvider(e.target.value)}
                  disabled={isRunning}
                  className="w-full pl-3 pr-8 py-2.5 text-sm border border-gray-300 rounded-lg appearance-none
                             focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
                >
                  <option value="claude">Claude (Anthropic)</option>
                  <option value="openai">OpenAI</option>
                  <option value="gemini">Google Gemini</option>
                </select>
                <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>
            </div>

            {/* Model */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                Model
              </label>
              <div className="relative">
                <select
                  value={modelName}
                  onChange={e => setModelName(e.target.value)}
                  disabled={isRunning || availableModels.length === 0}
                  className="w-full pl-3 pr-8 py-2.5 text-sm border border-gray-300 rounded-lg appearance-none
                             focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
                >
                  {availableModels.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
                <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* API key */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
              API Key <span className="text-red-400">*</span>
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                disabled={isRunning}
                placeholder="Paste your API key here"
                className="w-full px-3 pr-10 py-2.5 text-sm border border-gray-300 rounded-lg font-mono
                           focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              />
              <button
                type="button"
                onClick={() => setShowKey(v => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>

            {/* Security note */}
            <div className="flex items-start gap-1.5 mt-1.5">
              <Info size={12} className="text-blue-400 mt-0.5 flex-shrink-0" />
              <p className="text-gray-400 text-xs">
                API key is used only for this extraction and is <strong>never stored</strong> in the database.
              </p>
            </div>
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
                      ${page.extraction_status === 'completed' ? 'bg-green-50/50'   : ''}
                      ${page.extraction_status === 'failed'    ? 'bg-red-50/50'     : ''}
                      ${page.extraction_status === 'processing'? 'bg-blue-50/50'    : ''}
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
                { label: 'Equipment',   count: tagCounts.equipment,   cls: 'text-blue-700 bg-blue-50'   },
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
            disabled={isRunning || !apiKey.trim() || !modelName}
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
