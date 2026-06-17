import React, { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Settings, Cpu, Users, Factory, Save, Plus, ChevronDown,
  AlertCircle, Loader2, CheckCircle2, X, EyeOff, Eye,
  Shield, ShieldOff, Info, Pencil,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'

// ─────────────────────────────────────────────────────────────────────────────
// Section wrapper
// ─────────────────────────────────────────────────────────────────────────────
function Section({ icon: Icon, title, subtitle, children }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden mb-6">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100">
        <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
          <Icon size={16} className="text-blue-600" />
        </div>
        <div>
          <h2 className="font-semibold text-gray-900 text-sm">{title}</h2>
          {subtitle && <p className="text-gray-400 text-xs mt-0.5">{subtitle}</p>}
        </div>
      </div>
      <div className="p-6">{children}</div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// SECTION 1 — LLM Configuration
// ─────────────────────────────────────────────────────────────────────────────
function LlmConfigSection() {
  const [provider,  setProvider]  = useState('')
  const [modelName, setModelName] = useState('')
  const [apiKey,    setApiKey]    = useState('')
  const [showKey,   setShowKey]   = useState(false)
  const [saving,    setSaving]    = useState(false)
  const [saved,     setSaved]     = useState(false)
  const [error,     setError]     = useState('')

  const { data: current, isLoading: loadingCurrent } = useQuery({
    queryKey: ['llm-settings'],
    queryFn:  () => client.get('/api/settings/llm').then(r => r.data),
  })

  const { data: catalogue = {} } = useQuery({
    queryKey: ['llm-models'],
    queryFn:  () => client.get('/api/settings/llm/models').then(r => r.data),
  })

  React.useEffect(() => {
    if (current) {
      setProvider(current.provider || 'claude')
      setModelName(current.model_name || '')
    }
  }, [current])

  const models = catalogue[provider] || []

  async function handleSave(e) {
    e.preventDefault()
    if (!modelName) { setError('Please select a model.'); return }
    setSaving(true)
    setSaved(false)
    setError('')
    try {
      await client.post('/api/settings/llm', {
        provider,
        model_name: modelName,
        ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
      })
      setSaved(true)
      setApiKey('')
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Failed to save settings.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSave} className="space-y-4 max-w-lg">
      {error && (
        <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
          <AlertCircle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}
      {saved && (
        <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg px-3 py-2.5">
          <CheckCircle2 size={14} className="text-green-600" />
          <p className="text-green-700 text-sm">Settings saved.</p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Provider</label>
          <div className="relative">
            <select value={provider} onChange={e => { setProvider(e.target.value); setModelName('') }}
              disabled={loadingCurrent || saving}
              className="w-full pl-3 pr-8 py-2.5 text-sm border border-gray-300 rounded-lg appearance-none
                         focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50">
              <option value="claude">Claude</option>
              <option value="openai">OpenAI</option>
              <option value="gemini">Gemini</option>
            </select>
            <ChevronDown size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Default Model</label>
          <div className="relative">
            <select value={modelName} onChange={e => setModelName(e.target.value)}
              disabled={loadingCurrent || saving || models.length === 0}
              className="w-full pl-3 pr-8 py-2.5 text-sm border border-gray-300 rounded-lg appearance-none
                         focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50">
              <option value="">Select model…</option>
              {models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
            <ChevronDown size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          </div>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
          API Key {current?.api_key_hint && <span className="text-gray-400 normal-case font-normal">(current: ****{current.api_key_hint})</span>}
        </label>
        <div className="relative">
          <input type={showKey ? 'text' : 'password'} value={apiKey}
            onChange={e => setApiKey(e.target.value)} disabled={saving}
            placeholder="Enter new API key to update (leave blank to keep current)"
            className="w-full px-3 pr-10 py-2.5 text-sm border border-gray-300 rounded-lg font-mono
                       focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50" />
          <button type="button" onClick={() => setShowKey(v => !v)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
            {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>
        <div className="flex items-center gap-1 mt-1.5">
          <Info size={11} className="text-blue-400 flex-shrink-0" />
          <p className="text-gray-400 text-xs">Only the last 4 characters are stored for display. The full key is never retrievable.</p>
        </div>
      </div>

      <div className="flex justify-end">
        <button type="submit" disabled={saving || !provider || !modelName}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700
                     disabled:bg-blue-300 text-white text-sm font-medium rounded-lg transition-colors">
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
      </div>
    </form>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Add User Modal
// ─────────────────────────────────────────────────────────────────────────────
function AddUserModal({ onClose, onCreated }) {
  const [username,  setUsername]  = useState('')
  const [fullName,  setFullName]  = useState('')
  const [email,     setEmail]     = useState('')
  const [role,      setRole]      = useState('operator')
  const [password,  setPassword]  = useState('')
  const [showPw,    setShowPw]    = useState(false)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState('')

  React.useEffect(() => {
    function handler(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!username.trim() || !fullName.trim() || !password) {
      setError('Username, full name, and password are required.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await client.post('/api/users/', {
        username: username.trim(),
        full_name: fullName.trim(),
        email: email.trim() || undefined,
        role,
        password,
      })
      onCreated()
      onClose()
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Failed to create user.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Users size={16} className="text-blue-600" />
            <h2 className="font-semibold text-gray-900 text-base">Add User</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors">
            <X size={17} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
              <AlertCircle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                Username <span className="text-red-400">*</span>
              </label>
              <input type="text" value={username} onChange={e => setUsername(e.target.value)}
                placeholder="e.g. john.doe" required
                className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                Role <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <select value={role} onChange={e => setRole(e.target.value)}
                  className="w-full pl-3 pr-8 py-2.5 text-sm border border-gray-300 rounded-lg appearance-none
                             focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="viewer">Viewer</option>
                  <option value="operator">Operator</option>
                  <option value="admin">Admin</option>
                </select>
                <ChevronDown size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
              Full Name <span className="text-red-400">*</span>
            </label>
            <input type="text" value={fullName} onChange={e => setFullName(e.target.value)}
              placeholder="e.g. John Doe" required
              className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="john@example.com"
              className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
              Password <span className="text-red-400">*</span>
            </label>
            <div className="relative">
              <input type={showPw ? 'text' : 'password'} value={password}
                onChange={e => setPassword(e.target.value)} required placeholder="Set initial password"
                className="w-full px-3 pr-10 py-2.5 text-sm border border-gray-300 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <button type="button" onClick={() => setShowPw(v => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700
                         disabled:bg-blue-300 text-white text-sm font-medium rounded-lg transition-colors">
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              {loading ? 'Creating…' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// SECTION 2 — User Management
// ─────────────────────────────────────────────────────────────────────────────
const ROLE_CONFIG = {
  admin:    { cls: 'bg-red-100 text-red-700',    label: 'Admin' },
  operator: { cls: 'bg-blue-100 text-blue-700',  label: 'Operator' },
  viewer:   { cls: 'bg-gray-100 text-gray-600',  label: 'Viewer' },
}
function RoleBadge({ role }) {
  const cfg = ROLE_CONFIG[role] ?? ROLE_CONFIG.viewer
  return <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${cfg.cls}`}>{cfg.label}</span>
}

function UserManagementSection() {
  const { user: me } = useAuth()
  const queryClient  = useQueryClient()
  const [showAdd,    setShowAdd]    = useState(false)
  const [togglingId, setTogglingId] = useState(null)
  const [toggleErr,  setToggleErr]  = useState('')

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn:  () => client.get('/api/users/').then(r => r.data),
  })

  async function handleToggle(u) {
    if (u.id === me?.id) return
    setTogglingId(u.id)
    setToggleErr('')
    try {
      await client.patch(`/api/users/${u.id}/active`)
      queryClient.invalidateQueries({ queryKey: ['users'] })
    } catch (err) {
      setToggleErr(err.response?.data?.detail ?? 'Toggle failed.')
    } finally {
      setTogglingId(null)
    }
  }

  if (isLoading) {
    return <div className="flex justify-center py-8"><Loader2 size={20} className="animate-spin text-gray-400" /></div>
  }

  return (
    <>
      {toggleErr && (
        <div className="flex items-center gap-2 mb-3 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          <AlertCircle size={13} className="text-red-500" />
          <span className="text-red-600 text-xs">{toggleErr}</span>
        </div>
      )}
      <div className="overflow-x-auto rounded-xl border border-gray-200 mb-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100 text-left">
              <th className="px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">User</th>
              <th className="px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">Email</th>
              <th className="px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">Role</th>
              <th className="px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
              <th className="px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">Last Login</th>
              <th className="px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {users.map(u => (
              <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-800 text-xs">{u.full_name}</div>
                  <div className="text-gray-400 text-xs font-mono">{u.username}</div>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">{u.email ?? '—'}</td>
                <td className="px-4 py-3"><RoleBadge role={u.role} /></td>
                <td className="px-4 py-3">
                  {u.is_active
                    ? <span className="inline-flex items-center gap-1 text-green-700 text-xs"><Shield size={11} /> Active</span>
                    : <span className="inline-flex items-center gap-1 text-gray-400 text-xs"><ShieldOff size={11} /> Inactive</span>}
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">
                  {u.last_login
                    ? new Date(u.last_login).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
                    : '—'}
                </td>
                <td className="px-4 py-3 text-right">
                  {u.id === me?.id ? (
                    <span className="text-xs text-gray-300">You</span>
                  ) : (
                    <button onClick={() => handleToggle(u)} disabled={togglingId === u.id}
                      className={`text-xs px-3 py-1.5 rounded-lg border transition-colors flex items-center gap-1 ml-auto
                        ${u.is_active
                          ? 'border-red-200 text-red-600 hover:bg-red-50'
                          : 'border-green-200 text-green-600 hover:bg-green-50'}
                        disabled:opacity-40`}>
                      {togglingId === u.id
                        ? <Loader2 size={11} className="animate-spin" />
                        : u.is_active ? <ShieldOff size={11} /> : <Shield size={11} />}
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button onClick={() => setShowAdd(true)}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                   text-white text-sm font-medium rounded-lg transition-colors">
        <Plus size={14} /> Add User
      </button>
      {showAdd && (
        <AddUserModal
          onClose={() => setShowAdd(false)}
          onCreated={() => queryClient.invalidateQueries({ queryKey: ['users'] })}
        />
      )}
    </>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Edit Unit Modal
// ─────────────────────────────────────────────────────────────────────────────
function EditUnitModal({ unit, onClose, onSaved }) {
  const [unitCode,    setUnitCode]    = useState(unit.unit_code)
  const [unitName,    setUnitName]    = useState(unit.unit_name)
  const [description, setDescription] = useState(unit.description ?? '')
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState('')

  React.useEffect(() => {
    function handler(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!unitCode.trim() || !unitName.trim()) {
      setError('Unit code and name are required.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await client.put(`/api/units/${unit.id}`, {
        unit_code:   unitCode.trim().toUpperCase(),
        unit_name:   unitName.trim(),
        description: description.trim() || undefined,
      })
      onSaved()
      onClose()
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Failed to update unit.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Pencil size={15} className="text-blue-600" />
            <h2 className="font-semibold text-gray-900 text-base">Edit Unit</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors">
            <X size={17} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
              <AlertCircle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                Unit Code <span className="text-red-400">*</span>
              </label>
              <input type="text" value={unitCode} onChange={e => setUnitCode(e.target.value.toUpperCase())}
                required
                className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg font-mono
                           focus:outline-none focus:ring-2 focus:ring-blue-500 uppercase" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
                Unit Name <span className="text-red-400">*</span>
              </label>
              <input type="text" value={unitName} onChange={e => setUnitName(e.target.value)}
                required
                className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2}
              className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg resize-none
                         focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors">Cancel</button>
            <button type="submit" disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700
                         disabled:bg-blue-300 text-white text-sm font-medium rounded-lg transition-colors">
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              {loading ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// SECTION 3 — Process Units
// ─────────────────────────────────────────────────────────────────────────────
function ProcessUnitsSection() {
  const queryClient  = useQueryClient()
  const [editTarget, setEditTarget] = useState(null)

  const { data: units = [], isLoading } = useQuery({
    queryKey: ['units'],
    queryFn:  () => client.get('/api/units/').then(r => r.data),
  })

  if (isLoading) {
    return <div className="flex justify-center py-8"><Loader2 size={20} className="animate-spin text-gray-400" /></div>
  }

  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-gray-200 mb-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100 text-left">
              <th className="px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">Code</th>
              <th className="px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">Name</th>
              <th className="px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">Description</th>
              <th className="px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide text-right">Edit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {units.map(u => (
              <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-mono text-xs font-bold text-slate-700">{u.unit_code}</td>
                <td className="px-4 py-3 font-medium text-gray-800 text-sm">{u.unit_name}</td>
                <td className="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">{u.description ?? '—'}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => setEditTarget(u)} title="Edit unit"
                    className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                    <Pencil size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editTarget && (
        <EditUnitModal
          unit={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ['units'] })}
        />
      )}
    </>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Settings Page (admin-only)
// ─────────────────────────────────────────────────────────────────────────────
export default function SettingsPage() {
  const { user } = useAuth()

  if (user?.role !== 'admin') {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <Settings size={44} className="text-gray-200 mb-4" />
        <p className="text-gray-600 font-medium">Admin access required</p>
        <p className="text-gray-400 text-sm mt-1">Only administrators can access settings.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">Manage AI configuration, users, and process units</p>
      </div>

      <Section icon={Cpu} title="LLM Configuration"
        subtitle="Default AI provider and model for extraction and indexing">
        <LlmConfigSection />
      </Section>

      <Section icon={Users} title="User Management"
        subtitle="Create and manage operator accounts for your organisation">
        <UserManagementSection />
      </Section>

      <Section icon={Factory} title="Process Units"
        subtitle="Edit names and descriptions for configured process units">
        <ProcessUnitsSection />
      </Section>
    </div>
  )
}
