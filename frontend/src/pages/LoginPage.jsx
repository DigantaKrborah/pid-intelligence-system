import React, { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Loader2, AlertCircle, Activity } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

/**
 * LoginPage — the only public page in the app.
 * If the user is already logged in, redirect straight to /dashboard.
 */
export default function LoginPage() {
  const { login, isLoggedIn } = useAuth()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  // Already authenticated — skip the login page
  if (isLoggedIn) return <Navigate to="/dashboard" replace />

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username.trim(), password)
      // On success, AuthContext updates isLoggedIn → this component re-renders
      // and the `if (isLoggedIn)` above redirects to /dashboard automatically
    } catch (err) {
      // Show the error message from the backend, or a generic fallback
      const msg =
        err.response?.data?.detail ??
        'Login failed. Check your username and password.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">

        {/* ── Header card ──────────────────────────────────────────────── */}
        <div className="bg-slate-800 rounded-t-2xl px-8 pt-8 pb-6
                        border-b border-slate-700 text-center">
          {/* Logo placeholder — swap for <img> when you have a real logo */}
          <div className="w-14 h-14 bg-blue-600 rounded-2xl
                          flex items-center justify-center mx-auto mb-4">
            <Activity size={28} className="text-white" />
          </div>

          <h1 className="text-white text-xl font-bold tracking-tight">
            P&amp;ID Intelligence System
          </h1>
          <p className="text-slate-400 text-sm mt-1">Numaligarh Refinery Ltd</p>
        </div>

        {/* ── Login form card ───────────────────────────────────────────── */}
        <div className="bg-white rounded-b-2xl px-8 py-7 shadow-2xl">
          <h2 className="text-gray-800 text-base font-semibold mb-5">
            Sign in to your account
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Error banner — only shown when there is an error */}
            {error && (
              <div className="flex items-start gap-2.5 bg-red-50 border border-red-200
                              rounded-lg px-3 py-2.5">
                <AlertCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
                <p className="text-red-700 text-sm leading-snug">{error}</p>
              </div>
            )}

            {/* Username */}
            <div>
              <label
                htmlFor="username"
                className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide"
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading}
                autoComplete="username"
                autoFocus
                required
                placeholder="Enter your username"
                className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           disabled:bg-gray-50 disabled:text-gray-400 transition-shadow"
              />
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="password"
                className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                autoComplete="current-password"
                required
                placeholder="Enter your password"
                className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           disabled:bg-gray-50 disabled:text-gray-400 transition-shadow"
              />
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading || !username.trim() || !password}
              className="w-full py-2.5 px-4 mt-1
                         bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300
                         text-white text-sm font-semibold rounded-lg
                         transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  Signing in…
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Footer note */}
          <p className="text-gray-400 text-xs text-center mt-6 leading-relaxed">
            Authorized personnel only
            <br />
            Contact your administrator for access
          </p>
        </div>
      </div>
    </div>
  )
}
