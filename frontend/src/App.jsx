import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/Layout'

// Pages — each is a separate file in src/pages/
import LoginPage          from './pages/LoginPage'
import Dashboard          from './pages/Dashboard'
import UnitsPage          from './pages/UnitsPage'
import DrawingsPage       from './pages/DrawingsPage'
import DrawingDetailPage  from './pages/DrawingDetailPage'
import TagSearchPage      from './pages/TagSearchPage'
import TagDetailPage      from './pages/TagDetailPage'
import DocumentsPage      from './pages/DocumentsPage'
import SettingsPage       from './pages/SettingsPage'
import AuditPage          from './pages/AuditPage'

// One QueryClient instance for the whole app — caches API responses
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,           // retry failed requests once before showing an error
      staleTime: 30_000,  // cached data is fresh for 30 seconds
    },
  },
})

// ── Route guards ───────────────────────────────────────────────────────────────

/**
 * ProtectedRoute — redirects to /login if the user is not logged in.
 * Wraps the Layout + page content for every authenticated route.
 */
function ProtectedRoute({ children }) {
  const { isLoggedIn } = useAuth()
  if (!isLoggedIn) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

/**
 * AdminRoute — redirects to /login if not authenticated,
 * or to /dashboard if logged in but not admin.
 */
function AdminRoute({ children }) {
  const { isLoggedIn, user } = useAuth()
  if (!isLoggedIn) return <Navigate to="/login" replace />
  if (user?.role !== 'admin') return <Navigate to="/dashboard" replace />
  return <Layout>{children}</Layout>
}

// ── Route definitions ─────────────────────────────────────────────────────────
// AppRoutes is a separate component so it can call useAuth() (which needs AuthProvider above it)

function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />

      {/* Root → dashboard */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Protected — any logged-in role */}
      <Route path="/dashboard"     element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/units"         element={<ProtectedRoute><UnitsPage /></ProtectedRoute>} />
      <Route path="/drawings"      element={<ProtectedRoute><DrawingsPage /></ProtectedRoute>} />
      <Route path="/drawings/:id"  element={<ProtectedRoute><DrawingDetailPage /></ProtectedRoute>} />

      {/* /tags/search must come BEFORE /tags/:tagNumber so "search" isn't treated as a tag number */}
      <Route path="/tags/search"        element={<ProtectedRoute><TagSearchPage /></ProtectedRoute>} />
      <Route path="/tags/:tagNumber"    element={<ProtectedRoute><TagDetailPage /></ProtectedRoute>} />

      <Route path="/documents"     element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>} />

      {/* Admin only */}
      <Route path="/settings" element={<AdminRoute><SettingsPage /></AdminRoute>} />
      <Route path="/audit"    element={<AdminRoute><AuditPage /></AdminRoute>} />

      {/* Catch-all: send unknown paths to dashboard */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

// ── Root component ─────────────────────────────────────────────────────────────

export default function App() {
  return (
    // QueryClientProvider must wrap AuthProvider so API calls inside auth hooks are cached
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        {/* BrowserRouter must wrap AppRoutes so navigate/Link work */}
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
