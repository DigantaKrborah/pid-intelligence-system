import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Building2,
  FileText,
  Search,
  BookOpen,
  Settings,
  Clock,
  LogOut,
  ChevronRight,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

// Navigation items visible to all logged-in users
const NAV_ITEMS = [
  { path: '/dashboard',   label: 'Dashboard',    icon: LayoutDashboard },
  { path: '/units',       label: 'Units',        icon: Building2 },
  { path: '/drawings',    label: 'Drawings',     icon: FileText },
  { path: '/tags/search', label: 'Search Tags',  icon: Search },
  { path: '/documents',   label: 'Documents',    icon: BookOpen },
]

// Navigation items visible only to admins
const ADMIN_ITEMS = [
  { path: '/settings', label: 'Settings',  icon: Settings },
  { path: '/audit',    label: 'Audit Log', icon: Clock },
]

/**
 * Layout — wraps every protected page.
 * Renders a dark sidebar on the left and the page content on the right.
 *
 * Usage (in App.jsx):
 *   <Layout><Dashboard /></Layout>
 */
export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const location = useLocation()

  // Helper: is this nav link the current page?
  const isActive = (path) => location.pathname === path

  // Build a readable page title from the current path for the top bar
  const allItems = [...NAV_ITEMS, ...ADMIN_ITEMS]
  const currentItem = allItems.find((n) => location.pathname.startsWith(n.path))
  const pageTitle = currentItem?.label ?? 'P&ID Intelligence'

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">

      {/* ── Sidebar ────────────────────────────────────────────────────────── */}
      <aside className="w-60 flex-shrink-0 bg-slate-900 flex flex-col">

        {/* App name / logo area */}
        <div className="px-5 py-5 border-b border-slate-700/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-white text-xs font-bold">PI</span>
            </div>
            <div className="min-w-0">
              <p className="text-white text-sm font-semibold leading-tight truncate">P&amp;ID Intelligence</p>
              <p className="text-slate-400 text-xs leading-tight truncate">Numaligarh Refinery</p>
            </div>
          </div>
        </div>

        {/* Main navigation */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
            <Link
              key={path}
              to={path}
              className={`
                flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
                transition-colors duration-100
                ${isActive(path)
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }
              `}
            >
              <Icon size={16} className="flex-shrink-0" />
              {label}
            </Link>
          ))}

          {/* Admin section — only visible to admin users */}
          {user?.role === 'admin' && (
            <>
              <div className="pt-5 pb-1 px-3">
                <p className="text-slate-500 text-xs uppercase tracking-widest">Admin</p>
              </div>

              {ADMIN_ITEMS.map(({ path, label, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  className={`
                    flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
                    transition-colors duration-100
                    ${isActive(path)
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                    }
                  `}
                >
                  <Icon size={16} className="flex-shrink-0" />
                  {label}
                </Link>
              ))}
            </>
          )}
        </nav>

        {/* User info + logout at bottom of sidebar */}
        <div className="px-4 py-4 border-t border-slate-700/60">
          <div className="flex items-center gap-3">
            {/* Avatar initials */}
            <div className="w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-slate-200 text-xs font-semibold">
                {(user?.full_name ?? user?.username ?? '?')[0].toUpperCase()}
              </span>
            </div>

            <div className="min-w-0 flex-1">
              <p className="text-white text-sm font-medium truncate">
                {user?.full_name ?? user?.username}
              </p>
              <p className="text-slate-400 text-xs capitalize">{user?.role}</p>
            </div>

            {/* Logout button */}
            <button
              onClick={logout}
              title="Sign out"
              className="text-slate-400 hover:text-white p-1 rounded transition-colors"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main content area ──────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* Top bar */}
        <header className="h-13 flex-shrink-0 bg-white border-b border-gray-200
                           flex items-center px-6 gap-2">
          {/* Breadcrumb-style page title */}
          <span className="text-gray-400 text-sm">
            <ChevronRight size={14} className="inline" />
          </span>
          <h1 className="text-gray-700 text-sm font-medium">{pageTitle}</h1>
        </header>

        {/* Page content — scrollable */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
