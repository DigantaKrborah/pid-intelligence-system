import React, { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Upload, X, AlertCircle, FileText, ChevronDown, Loader2 } from 'lucide-react'
import client from '../api/client'

const MAX_SIZE_BYTES = 50 * 1024 * 1024  // 50 MB

// Supported document types — must match backend _VALID_DOC_TYPES exactly
const DOC_TYPES = [
  { value: 'OPERATING_MANUAL', label: 'Operating Manual' },
  { value: 'SOP',              label: 'SOP (Standard Operating Procedure)' },
  { value: 'DATASHEET',        label: 'Datasheet' },
  { value: 'OTHER',            label: 'Other' },
]

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function UploadDocumentModal({ onClose, onSuccess, defaultUnitId = '' }) {
  const [unitId,    setUnitId]    = useState(defaultUnitId)
  const [docType,   setDocType]   = useState('OPERATING_MANUAL')
  const [docTitle,  setDocTitle]  = useState('')
  const [file,      setFile]      = useState(null)
  const [fileError, setFileError] = useState('')
  const [submitErr, setSubmitErr] = useState('')
  const [uploading, setUploading] = useState(false)
  const [progress,  setProgress]  = useState(0)

  const fileRef = useRef()

  // Close on Escape unless uploading
  useEffect(() => {
    function handler(e) { if (e.key === 'Escape' && !uploading) onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose, uploading])

  const { data: units = [] } = useQuery({
    queryKey: ['units'],
    queryFn:  () => client.get('/api/units/').then(r => r.data),
  })

  function handleFileChange(e) {
    const f = e.target.files[0]
    if (!f) return
    const ext = f.name.split('.').pop().toLowerCase()
    if (ext !== 'pdf') {
      setFileError('Only PDF files are accepted for documents.')
      e.target.value = ''
      return
    }
    if (f.size > MAX_SIZE_BYTES) {
      setFileError(`File too large (${formatSize(f.size)}). Maximum is 50 MB.`)
      e.target.value = ''
      return
    }
    setFileError('')
    setSubmitErr('')
    setFile(f)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!file) { setSubmitErr('Please select a PDF file.'); return }
    setSubmitErr('')
    setUploading(true)
    setProgress(0)

    const formData = new FormData()
    formData.append('unit_id',   unitId)
    formData.append('doc_type',  docType)
    formData.append('doc_title', docTitle.trim())
    formData.append('file',      file)

    try {
      // axios auto-sets multipart/form-data with boundary when given FormData
      await client.post('/api/documents/upload', formData, {
        onUploadProgress: (ev) => {
          if (ev.total) setProgress(Math.round((ev.loaded / ev.total) * 100))
        },
      })
      onSuccess()
      onClose()
    } catch (err) {
      const msg = err.response?.data?.detail
      setSubmitErr(typeof msg === 'string' ? msg : 'Upload failed. Please try again.')
      setUploading(false)
      setProgress(0)
    }
  }

  const canSubmit = unitId && docTitle.trim() && file && !uploading

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={e => { if (e.target === e.currentTarget && !uploading) onClose() }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Upload size={17} className="text-blue-600" />
            <h2 className="text-gray-800 font-semibold text-base">Upload Document</h2>
          </div>
          <button
            onClick={onClose}
            disabled={uploading}
            className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors disabled:opacity-40"
          >
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">

          {submitErr && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
              <AlertCircle size={15} className="text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-red-700 text-sm">{submitErr}</p>
            </div>
          )}

          {/* Unit */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
              Process Unit <span className="text-red-400">*</span>
            </label>
            <div className="relative">
              <select
                value={unitId}
                onChange={e => setUnitId(e.target.value)}
                required disabled={uploading}
                className="w-full pl-3 pr-8 py-2.5 text-sm border border-gray-300 rounded-lg appearance-none
                           focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              >
                <option value="">Select a unit…</option>
                {units.map(u => (
                  <option key={u.id} value={u.id}>{u.unit_code} — {u.unit_name}</option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* Document type + title side by side on wider screens */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                Document Type <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <select
                  value={docType}
                  onChange={e => setDocType(e.target.value)}
                  disabled={uploading}
                  className="w-full pl-3 pr-8 py-2.5 text-sm border border-gray-300 rounded-lg appearance-none
                             focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
                >
                  {DOC_TYPES.map(dt => (
                    <option key={dt.value} value={dt.value}>{dt.label}</option>
                  ))}
                </select>
                <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                Document Title <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={docTitle}
                onChange={e => setDocTitle(e.target.value)}
                required disabled={uploading}
                placeholder="e.g. CDU Operating Manual"
                className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              />
            </div>
          </div>

          {/* File upload */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
              PDF File <span className="text-red-400">*</span>
            </label>

            {file ? (
              <div className="flex items-center gap-3 px-3 py-3 bg-green-50 border border-green-200 rounded-lg">
                <FileText size={18} className="text-green-600 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{file.name}</p>
                  <p className="text-xs text-gray-500">{formatSize(file.size)}</p>
                </div>
                {!uploading && (
                  <button type="button" onClick={() => { setFile(null); fileRef.current.value = '' }}
                    className="text-gray-400 hover:text-red-500 p-1 rounded transition-colors">
                    <X size={13} />
                  </button>
                )}
              </div>
            ) : (
              <button type="button" onClick={() => fileRef.current?.click()} disabled={uploading}
                className="w-full border-2 border-dashed border-gray-300 rounded-lg py-5
                           flex flex-col items-center gap-2 text-gray-400
                           hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50
                           transition-colors disabled:opacity-50"
              >
                <Upload size={22} />
                <span className="text-sm">Click to select a PDF</span>
                <span className="text-xs">Maximum 50 MB</span>
              </button>
            )}

            <input ref={fileRef} type="file" accept=".pdf" onChange={handleFileChange} className="hidden" />

            {fileError && (
              <p className="text-red-500 text-xs mt-1.5 flex items-center gap-1">
                <AlertCircle size={11} />{fileError}
              </p>
            )}
          </div>

          {/* Progress bar */}
          {uploading && (
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-xs text-gray-500">Uploading…</span>
                <span className="text-xs font-medium text-blue-600">{progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div className="bg-blue-600 h-1.5 rounded-full transition-all" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          {/* Buttons */}
          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={onClose} disabled={uploading}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors disabled:opacity-40">
              Cancel
            </button>
            <button type="submit" disabled={!canSubmit}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300
                         text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2">
              {uploading
                ? <><Loader2 size={14} className="animate-spin" /> Uploading…</>
                : <><Upload size={14} /> Upload</>}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
