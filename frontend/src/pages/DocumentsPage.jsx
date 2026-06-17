import React, { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen, Upload, Zap, Eye, Trash2, AlertCircle, Loader2,
  CheckCircle2, XCircle, Clock, X, ChevronDown, Info,
  EyeOff, Tag,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import UploadDocumentModal from '../components/UploadDocumentModal'

// ── Document type badge ────────────────────────────────────────────────────────
const DOC_TYPE_CONFIG = {
  OPERATING_MANUAL: { cls: 'bg-blue-50 text-blue-700',    label: 'Operating Manual' },
  SOP:              { cls: 'bg-purple-50 text-purple-700', label: 'SOP' },
  DATASHEET:        { cls: 'bg-orange-50 text-orange-700', label: 'Datasheet' },
  OTHER:            { cls: 'bg-gray-100 text-gray-600',    label: 'Other' },
}
function DocTypeBadge({ docType }) {
  const cfg = DOC_TYPE_CONFIG[docType] ?? DOC_TYPE_CONFIG.OTHER
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  )
}

// ── Processing status badge ────────────────────────────────────────────────────
const STATUS_CONFIG = {
  uploaded:   { cls: 'bg-gray-100 text-gray-600',     label: 'Uploaded',    icon: <Clock size={11} /> },
  processing: { cls: 'bg-yellow-100 text-yellow-700', label: 'Processing…', icon: <Loader2 size={11} className="animate-spin" /> },
  indexed:    { cls: 'bg-green-100 text-green-700',   label: 'Indexed',     icon: <CheckCircle2 size={11} /> },
  failed:     { cls: 'bg-red-100 text-red-700',       label: 'Failed',      icon: <XCircle size={11} /> },
}
function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.uploaded
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.icon}{cfg.label}
    </span>
  )
}

// ── Index Document Modal ───────────────────────────────────────────────────────
// /api/documents/{id}/index is SYNCHRONOUS — may take several minutes for long docs.
function IndexDocumentModal({ document, onClose, onDone }) {
  const [provider,  setProvider]  = useState('claude')
  const [modelName, setModelName] = useState('')
  const [apiKey,    setApiKey]    = useState('')
  const [showKey,   setShowKey]   = useState(false)
  const [running,   setRunning]   = useState(false)
  const [result,    setResult]    = useState(null)
  const [error,     setError]     = useState('')

  const { data: catalogue = {} } = useQuery({
    queryKey: ['llm-models'],
    queryFn:  () => client.get('/api/settings/llm/models').then(r => r.data),
  })
  const models = catalogue[provider] || []

  React.useEffect(() => {
    if (models.length > 0) setModelName(models[0].id)
    else                   setModelName('')
  }, [provider, models.length])

  async function handleStart() {
    if (!apiKey.trim()) { setError('Please enter your API key.'); return }
    if (!modelName)     { setError('Please select a model.');    return }
    setError('')
    setRunning(true)
    try {
      const { data } = await client.post(
        `/api/documents/${document.id}/index`,
        { provider, model_name: modelName, api_key: apiKey },
        { timeout: 600_000 },  // 10 min — large PDFs can take a long time
      )
      setResult(data)
      onDone()
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Indexing failed. Check your API key and try again.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={e => { if (e.target === e.currentTarget && !running) onClose() }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">

        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <Zap size={15} className="text-yellow-500" />
              <h2 className="text-gray-800 font-semibold text-base">Index Document</h2>
            </div>
            <p className="text-gray-400 text-xs truncate max-w-xs">{document.doc_title}</p>
          </div>
          <button onClick={onClose} disabled={running}
            className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors disabled:opacity-30">
            <X size={17} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {error && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
              <AlertCircle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          {result ? (
            <div className="text-center py-4">
              <CheckCircle2 size={36} className="text-green-500 mx-auto mb-3" />
              <p className="text-gray-800 font-medium">Indexing Complete</p>
              <div className="flex justify-center gap-6 mt-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-blue-700">{result.total_tags_found}</p>
                  <p className="text-xs text-gray-400">Tag References</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-700">{result.pages_processed}</p>
                  <p className="text-xs text-gray-400">Pages Processed</p>
                </div>
              </div>
              {result.warning && (
                <p className="text-amber-600 text-xs mt-3 bg-amber-50 px-3 py-2 rounded-lg">{result.warning}</p>
              )}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Provider</label>
                  <div className="relative">
                    <select value={provider} onChange={e => setProvider(e.target.value)} disabled={running}
                      className="w-full pl-3 pr-7 py-2 text-sm border border-gray-300 rounded-lg appearance-none
                                 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50">
                      <option value="claude">Claude</option>
                      <option value="openai">OpenAI</option>
                      <option value="gemini">Gemini</option>
                    </select>
                    <ChevronDown size={13} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Model</label>
                  <div className="relative">
                    <select value={modelName} onChange={e => setModelName(e.target.value)}
                      disabled={running || models.length === 0}
                      className="w-full pl-3 pr-7 py-2 text-sm border border-gray-300 rounded-lg appearance-none
                                 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50">
                      {models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                    </select>
                    <ChevronDown size={13} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                  API Key <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <input type={showKey ? 'text' : 'password'} value={apiKey}
                    onChange={e => setApiKey(e.target.value)} disabled={running}
                    placeholder="Paste your API key"
                    className="w-full px-3 pr-10 py-2.5 text-sm border border-gray-300 rounded-lg font-mono
                               focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50" />
                  <button type="button" onClick={() => setShowKey(v => !v)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                    {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
                <div className="flex items-center gap-1 mt-1.5">
                  <Info size={11} className="text-blue-400 flex-shrink-0" />
                  <p className="text-gray-400 text-xs">API key is never stored. Large documents may take several minutes.</p>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-100 flex justify-between">
          <button onClick={onClose} disabled={running}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors disabled:opacity-30">
            {running ? 'Indexing in progress…' : result ? 'Close' : 'Cancel'}
          </button>
          {!result && (
            <button onClick={handleStart} disabled={running || !apiKey.trim() || !modelName}
              className="flex items-center gap-2 px-5 py-2 bg-yellow-500 hover:bg-yellow-600
                         disabled:bg-gray-200 disabled:text-gray-400
                         text-white text-sm font-medium rounded-lg transition-colors">
              {running
                ? <><Loader2 size={14} className="animate-spin" /> Indexing…</>
                : <><Zap size={14} /> Start Indexing</>}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Document View Modal ────────────────────────────────────────────────────────
function DocumentViewModal({ documentId, onClose }) {
  const { data: doc, isLoading, error } = useQuery({
    queryKey: ['documentDetail', documentId],
    queryFn:  () => client.get(`/api/documents/${documentId}`).then(r => r.data),
    enabled:  !!documentId,
  })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">

        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100 flex-shrink-0">
          <div>
            <h2 className="text-gray-800 font-semibold text-base">{doc?.doc_title ?? 'Document'}</h2>
            <p className="text-gray-400 text-xs mt-0.5">
              {doc?.tag_reference_count ?? 0} tag reference{doc?.tag_reference_count !== 1 ? 's' : ''} indexed
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors">
            <X size={17} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {isLoading && (
            <div className="flex justify-center py-12">
              <Loader2 size={24} className="animate-spin text-gray-400" />
            </div>
          )}
          {error && <p className="text-red-500 text-sm text-center py-8">Failed to load document.</p>}
          {doc && !isLoading && (
            <>
              {!doc.tag_references?.length ? (
                <div className="text-center py-12">
                  <Tag size={36} className="text-gray-200 mx-auto mb-3" />
                  <p className="text-gray-500 text-sm">No tag references indexed yet.</p>
                  <p className="text-gray-400 text-xs mt-1">Run indexing to extract tag mentions from this document.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {doc.tag_references.map((ref, i) => (
                    <div key={ref.id ?? i} className="border border-gray-200 rounded-lg px-4 py-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs font-bold text-blue-700">{ref.tag_number}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-400">p. {ref.page_number}</span>
                          {ref.context_type && (
                            <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                              {ref.context_type}
                            </span>
                          )}
                        </div>
                      </div>
                      {ref.section_title && (
                        <p className="text-xs text-gray-500 mb-1">{ref.section_title}</p>
                      )}
                      {ref.context_text && (
                        <p className="text-xs text-gray-600 italic">{ref.context_text}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Delete confirm dialog ──────────────────────────────────────────────────────
function DeleteConfirmDialog({ document, onCancel, onConfirm, loading }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={e => { if (e.target === e.currentTarget) onCancel() }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
            <Trash2 size={17} className="text-red-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 text-sm">Delete Document</h3>
            <p className="text-gray-400 text-xs">This cannot be undone</p>
          </div>
        </div>
        <p className="text-gray-600 text-sm mb-5">
          Delete <strong>"{document.doc_title}"</strong>? The file and all indexed tag references will be permanently removed.
        </p>
        <div className="flex justify-end gap-3">
          <button onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors">
            Cancel
          </button>
          <button onClick={onConfirm} disabled={loading}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white text-sm
                       font-medium rounded-lg transition-colors flex items-center gap-2">
            {loading ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
            {loading ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Documents Page ─────────────────────────────────────────────────────────────
export default function DocumentsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const [selectedUnit,  setSelectedUnit]  = useState('')
  const [showUpload,    setShowUpload]     = useState(false)
  const [indexTarget,   setIndexTarget]   = useState(null)
  const [viewTarget,    setViewTarget]    = useState(null)
  const [deleteTarget,  setDeleteTarget]  = useState(null)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError,   setDeleteError]   = useState('')

  const isAdmin = user?.role === 'admin'

  const { data: units = [] } = useQuery({
    queryKey: ['units'],
    queryFn:  () => client.get('/api/units/').then(r => r.data),
  })

  const { data: documents = [], isLoading, error } = useQuery({
    queryKey: ['documents', selectedUnit],
    queryFn:  () => {
      const url = selectedUnit ? `/api/documents/?unit_id=${selectedUnit}` : '/api/documents/'
      return client.get(url).then(r => r.data)
    },
  })

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleteLoading(true)
    setDeleteError('')
    try {
      await client.delete(`/api/documents/${deleteTarget.id}`)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setDeleteTarget(null)
    } catch (err) {
      setDeleteError(err.response?.data?.detail ?? 'Delete failed.')
    } finally {
      setDeleteLoading(false)
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Operating Manuals &amp; SOPs</h1>
          <p className="text-gray-500 text-sm mt-1">
            {documents.length} document{documents.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button onClick={() => setShowUpload(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                     text-white text-sm font-medium rounded-lg transition-colors shadow-sm">
          <Upload size={15} />
          Upload Document
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 bg-white rounded-xl border border-gray-200 shadow-sm px-4 py-3 mb-4">
        <span className="text-gray-500 text-sm flex-shrink-0">Filter by unit:</span>
        <div className="relative">
          <select value={selectedUnit} onChange={e => setSelectedUnit(e.target.value)}
            className="pl-3 pr-8 py-1.5 text-sm border border-gray-300 rounded-lg appearance-none
                       focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
            <option value="">All Units</option>
            {units.map(u => <option key={u.id} value={u.id}>{u.unit_code} — {u.unit_name}</option>)}
          </select>
          <ChevronDown size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>
        {selectedUnit && (
          <button onClick={() => setSelectedUnit('')} className="text-xs text-blue-600 hover:underline">
            Clear
          </button>
        )}
      </div>

      {isLoading && (
        <div className="flex justify-center py-16">
          <Loader2 size={26} className="animate-spin text-gray-400" />
        </div>
      )}

      {error && !isLoading && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4">
          <AlertCircle size={16} className="text-red-500" />
          <p className="text-red-700 text-sm">Failed to load documents.</p>
        </div>
      )}

      {!isLoading && !error && documents.length === 0 && (
        <div className="flex flex-col items-center py-16 text-center bg-white rounded-xl border border-gray-200">
          <BookOpen size={44} className="text-gray-200 mb-4" />
          <p className="text-gray-600 font-medium">No documents yet</p>
          <p className="text-gray-400 text-sm mt-1">
            Upload operating manuals or SOPs to link them to equipment tags.
          </p>
        </div>
      )}

      {!isLoading && documents.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {deleteError && (
            <div className="bg-red-50 border-b border-red-200 px-4 py-2 flex items-center gap-2">
              <AlertCircle size={13} className="text-red-500" />
              <span className="text-red-600 text-xs">{deleteError}</span>
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-left">
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Title</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Type</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Unit</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide text-center w-16">Pages</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide text-center w-20">Tags</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Uploaded</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {documents.map(doc => (
                  <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-800 max-w-xs">
                      <span className="block truncate">{doc.doc_title}</span>
                    </td>
                    <td className="px-4 py-3"><DocTypeBadge docType={doc.doc_type} /></td>
                    <td className="px-4 py-3">
                      <span className="bg-slate-100 text-slate-700 text-xs font-semibold px-2 py-0.5 rounded">
                        {doc.unit_code}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-center">{doc.total_pages ?? '—'}</td>
                    <td className="px-4 py-3 text-center">
                      {doc.tag_reference_count > 0
                        ? <span className="font-medium text-blue-700">{doc.tag_reference_count}</span>
                        : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={doc.processing_status} /></td>
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {new Date(doc.uploaded_at).toLocaleDateString('en-IN', {
                        day: '2-digit', month: 'short', year: 'numeric',
                      })}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1.5">
                        <button onClick={() => setIndexTarget(doc)}
                          disabled={doc.processing_status === 'processing'}
                          title="Run AI indexing"
                          className="p-1.5 text-gray-400 hover:text-yellow-600 hover:bg-yellow-50
                                     rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                          <Zap size={14} />
                        </button>
                        <button onClick={() => setViewTarget(doc.id)} title="View indexed tags"
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                          <Eye size={14} />
                        </button>
                        {isAdmin && (
                          <button onClick={() => { setDeleteError(''); setDeleteTarget(doc) }} title="Delete"
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                            <Trash2 size={14} />
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

      {showUpload && (
        <UploadDocumentModal
          onClose={() => setShowUpload(false)}
          onSuccess={() => queryClient.invalidateQueries({ queryKey: ['documents'] })}
          defaultUnitId={selectedUnit}
        />
      )}
      {indexTarget && (
        <IndexDocumentModal
          document={indexTarget}
          onClose={() => setIndexTarget(null)}
          onDone={() => queryClient.invalidateQueries({ queryKey: ['documents'] })}
        />
      )}
      {viewTarget && (
        <DocumentViewModal
          documentId={viewTarget}
          onClose={() => setViewTarget(null)}
        />
      )}
      {deleteTarget && (
        <DeleteConfirmDialog
          document={deleteTarget}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
          loading={deleteLoading}
        />
      )}
    </div>
  )
}
