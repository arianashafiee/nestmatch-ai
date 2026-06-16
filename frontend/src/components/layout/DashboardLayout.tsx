import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { BarChart3, Home, Kanban } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { TopNavbar } from './TopNavbar'
import { cn } from '@/lib/utils'

const mobileNavItems = [
  { to: '/', label: 'Home', icon: Home, end: true },
  { to: '/board', label: 'Board', icon: Kanban },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
]

export function DashboardLayout() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  return (
    <div className="flex min-h-svh bg-white">
      <Sidebar />

      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 md:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
          aria-hidden
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 transform border-r border-slate-200 bg-slate-50 transition-transform md:hidden',
          isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-16 items-center gap-2 border-b border-slate-200 px-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
            N
          </div>
          <span className="text-lg font-semibold text-slate-900">NestMatch</span>
        </div>
        <nav className="flex flex-col gap-1 p-4">
          {mobileNavItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setIsMobileMenuOpen(false)}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:bg-slate-100',
                )
              }
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <TopNavbar
          onMenuToggle={() => setIsMobileMenuOpen((open) => !open)}
          isMobileMenuOpen={isMobileMenuOpen}
        />
        <main className="flex-1 overflow-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
