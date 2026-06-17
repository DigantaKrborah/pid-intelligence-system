import React, { createContext, useContext, useState } from 'react'
import client from '../api/client'

// Create the context object — null default catches usage outside the provider
const AuthContext = createContext(null)

/**
 * AuthProvider — wrap the entire app with this so any component can call useAuth().
 * It reads the saved token/user from localStorage on first load so the user stays
 * logged in across page refreshes.
 */
export function AuthProvider({ children }) {
  // Restore persisted login from localStorage (runs once on mount)
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('pid_user')
    try { return saved ? JSON.parse(saved) : null }
    catch { return null }
  })

  const [token, setToken] = useState(() => localStorage.getItem('pid_token'))

  // True only when we have both a token AND a user object
  const isLoggedIn = Boolean(token && user)

  /**
   * login(username, password)
   * Calls POST /api/auth/login, saves the token + user to state and localStorage.
   * Throws the original Axios error on failure so the caller can show a message.
   */
  async function login(username, password) {
    const { data } = await client.post('/api/auth/login', { username, password })

    const { access_token, user: userData } = data

    // Save to React state
    setToken(access_token)
    setUser(userData)

    // Save to localStorage so the values survive a page refresh
    localStorage.setItem('pid_token', access_token)
    localStorage.setItem('pid_user', JSON.stringify(userData))

    return userData
  }

  /**
   * logout()
   * Clears all stored credentials and redirects to /login.
   */
  function logout() {
    setToken(null)
    setUser(null)
    localStorage.removeItem('pid_token')
    localStorage.removeItem('pid_user')
    // Hard redirect — fully resets React state
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoggedIn, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

/**
 * useAuth() — convenience hook.
 * Returns { user, token, isLoggedIn, login, logout }
 */
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
