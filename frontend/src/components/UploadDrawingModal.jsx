import React, { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Upload, X, AlertCircle, FileText, CheckCircle2, ChevronDown, Loader2,
} from 'lucide-react'
import client from '../api/client'

// Accepted file extensions — must match backend validate_file_type()
const ACCEPTED_TYPES = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff']
const MAX_SIZE_MB    = 50
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

// Format bytes into a human-readable string (e.g. "2.4 MB")
function formatSize(bytes) {
  if (bytes < 1024)             return `${bytes} B`
  if (bytes < 1024 * 1024)      return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function UploadDrawingModal({ onClose, onSuccess, defaultUnitId = '' }) {
  const [unitId, setUnitId]           = useState(defaultUnitId)
  const [drawingNumber, setDrawingNumber] = useState('')
  const [drawingTitle, setDrawingTitle]   = useState('')
  const [revision, setRevision]           = useState('')
  const [file, setFile]                   = useState(null)
  const [fileError, setFileError]         = useState('')
  const [submitError, setSubmitError]     = useState('')
  const [uploading, setUploading]         = useState(false)
  const [progress, setProgress]           = useState(0)  // 0–100 during upload

  const fileInputRef = useRef()

  // Close on Escape key
  useEffect(() => {
    function handler(e) { if (e.key === 'Escape' && !uploading) onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose, uploading])

  // Fetch units for the dropdown
  const { data: units = [] } = useQuery({
    queryKey: ['units'],
    queryFn:  () => client.get('/api/units/').then(r => r.data),
  })

  // ── File selection ─────────────────────────────────────────────────────────
  function handleFileChange(e) {
    const selected = e.target.files[0]
    if (!selected) return

    // Validate extension
    const ext = '.' + selected.name.split('.').pop().toLowerCase()
    if (!ACCEPTED_TYPES.includes(ext)) {
      setFileError(`File type not allowed. Accepted: ${ACCEPTED_TYPES.join(', ')}`)
      e.target.value = ''
      return
    }

    // Validate size
    if (selected.size > MAX_SIZE_BYTES) {
      setFileError(`File is too large (${formatSize(selected.size)}). Maximum is ${MAX_SIZE_MB} MB.`)
      e.target.value = ''
      return
    }

    setFileError('')
    setSubmitError('')
    setFile(selected)
  }

  function clearFile() {
    setFile(null)
    setFileError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // ── Form submit ────────────────────────────────────────────────────────────
  async function handleSubmit(e) {
    e.preventDefault()
    if (!file) { setSubmitError('Please select a file.'); return }

    setSubmitError('')
    setUploading(true)
    setProgress(0)

    // Build multipart form data — FastAPI reads each field from Form(...)
    const formData = new FormData()
    formData.append('unit_id',       unitId)
    formData.append('drawing_number', drawingNumber.trim())
    if (drawingTitle.trim()) formData.append('drawing_title', drawingTitle.trim())
    if (revision.trim())     formData.append('revision',      revision.trim())
    formData.append('file', file)

    try {
      // Note: do NOT manually set Content-Type here.
      // When axios receives FormData, it automatically sets multipart/form-data
      // with the correct boundary string — setting it manually would break the request.
      await client.post('/api/drawings/upload', formData, {
        onUploadProgress: (event) => {
          if (event.total) {
            setProgress(Math.round((event.loaded / event.total) * 100))
          }
        },
      })

      onSuccess()  // tell DrawingsPage to refresh the table
      onClose()
    } catch (err) {
      const msg = err.response?.data?.detail
      setSubmitError(
        typeof msg === 'string' ? msg : 'Upload failed. Please check your inputs and try again.'
      )
      setUploading(false)
      setProgress(0)
    }
  }

  const canSubmit = unitId && drawingNumber.trim() && file && !uploading

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget && !uploading) onClose() }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">

        {/* ── Modal header ─────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Upload size={18} className="text-blue-600" />
            <h2 className="text-gray-800 font-semibold text-base">Upload P&amp;ID Drawing</h2>
          </div>
          <button
            onClick={onClose}
            disabled={uploading}
            className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors disabled:opacity-40"
          >
            <X size={18} />
          </button>
        </div>

        {/* ── Form ─────────────────────────────────────────────────────── */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">

          {/* Submit error */}
          {submitError && (
            <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
              <AlertCircle size={15} className="text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-red-700 text-sm">{submitError}</p>
            </div>
          )}

          {/* Unit selection */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
              Process Unit <span className="text-red-400">*</span>
            </label>
            <div className="relative">
              <select
                value={unitId}
                onChange={e => setUnitId(e.target.value)}
                required
                disabled={uploading}
                className="w-full pl-3 pr-8 py-2.5 text-sm border border-gray-300 rounded-lg appearance-none
                           focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              >
                <option value="">Select a unit…</option>
                {units.map(u => (
                  <option key={u.id} value={u.id}>
                    {u.unit_code} — {u.unit_name}
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* Drawing number + revision — side by side */}
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                Drawing Number <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={drawingNumber}
                onChange={e => setDrawingNumber(e.target.value)}
                required
                disabled={uploading}
                placeholder="e.g. NRL-CDU-PID-001"
                className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg font-mono
                           focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                Revision
              </label>
              <input
                type="text"
                value={revision}
                onChange={e => setRevision(e.target.value)}
                disabled={uploading}
                placeholder="R3"
                maxLength={10}
                className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg font-mono
                           focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              />
            </div>
          </div>

          {/* Drawing title */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
              Title <span className="text-gray-400 font-normal normal-case">(optional)</span>
            </label>
            <input
              type="text"
              value={drawingTitle}
              onChange={e => setDrawingTitle(e.target.value)}
              disabled={uploading}
              placeholder="e.g. Atmospheric Distillation Column Overhead System"
              className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
            />
          </div>

          {/* File upload */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
              File <span className="text-red-400">*</span>
            </label>

            {file ? (
              /* ── Selected file preview ─────────────────────────────── */
              <div className="flex items-center gap-3 px-3 py-3 bg-green-50 border border-green-200 rounded-lg">
                <FileText size={20} className="text-green-600 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{file.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{formatSize(file.size)}</p>
                </div>
                {!uploading && (
                  <button
                    type="button"
                    onClick={clearFile}
                    className="text-gray-400 hover:text-red-500 p-1 rounded transition-colors"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            ) : (
              /* ── Drop zone ─────────────────────────────────────────── */
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="w-full border-2 border-dashed border-gray-300 rounded-lg py-6
                           flex flex-col items-center gap-2 text-gray-400
                           hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50
                           transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Upload size={24} />
                <span className="text-sm">Click to select a file</span>
                <span className="text-xs">PDF, JPG, PNG, TIFF — max {MAX_SIZE_MB} MB</span>
              </button>
            )}

            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_TYPES.join(',')}
              onChange={handleFileChange}
              className="hidden"
            />

            {fileError && (
              <p className="text-red-500 text-xs mt-1.5 flex items-center gap-1">
                <AlertCircle size={12} />
                {fileError}
              </p>
            )}
          </div>

          {/* ── Upload progress bar ───────────────────────────────────── */}
          {uploading && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-gray-500">Uploading…</span>
                <span className="text-xs font-medium text-blue-600">{progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-200"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-1.5">
                Please wait — large PDFs may take a moment to convert to page images.
              </p>
            </div>
          )}

          {/* ── Action buttons ────────────────────────────────────────── */}
          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={uploading}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors disabled:opacity-40"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300
                         text-white text-sm font-medium rounded-lg transition-colors
                         flex items-center gap-2"
            >
              {uploading ? (
                <><Loader2 size={14} className="animate-spin" /> Uploading…</>
              ) : (
                <><Upload size={14} /> Upload Drawing</>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
