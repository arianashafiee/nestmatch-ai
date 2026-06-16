import { Link, useLocation } from 'react-router-dom'
import { Bell, Menu, Plus, Search, X } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useApartments } from '@/context/ApartmentsContext'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { cn } from '@/lib/utils'

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/profile': 'Student Profile',
  '/board': 'Hunting Board',
  '/analytics': 'Analytics',
}

function getPageTitle(pathname: string): string {
  if (pathname.startsWith('/board/')) return 'Listing Analysis'
  return pageTitles[pathname] ?? 'NestMatch AI'
}

interface TopNavbarProps {
  onMenuToggle?: () => void
  isMobileMenuOpen?: boolean
}

export function TopNavbar({ onMenuToggle, isMobileMenuOpen }: TopNavbarProps) {
  const location = useLocation()
  const { profile, isProfileComplete } = useStudentProfile()
  const { openAddModal } = useApartments()
  const title = getPageTitle(location.pathname)

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuToggle}
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 md:hidden"
          aria-label="Toggle menu"
        >
          {isMobileMenuOpen ? (
            <X className="h-5 w-5" />
          ) : (
            <Menu className="h-5 w-5" />
          )}
        </button>
        <div>
          <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
          {profile.university && (
            <p className="text-xs text-slate-500">{profile.university}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-4">
        <Button
          size="sm"
          onClick={openAddModal}
          className="hidden sm:inline-flex"
        >
          <Plus className="h-4 w-4" />
          Find Apartments
        </Button>

        <div className="hidden items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 lg:flex">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            type="search"
            placeholder="Search listings..."
            className="w-40 bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-400 lg:w-56"
            disabled
          />
        </div>

        {!isProfileComplete && (
          <Link
            to="/profile"
            className="hidden rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 sm:inline-block"
          >
            Complete your profile
          </Link>
        )}

        <button
          type="button"
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
        </button>

        <div
          className={cn(
            'flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold',
            isProfileComplete
              ? 'bg-indigo-100 text-indigo-700'
              : 'bg-slate-100 text-slate-500',
          )}
        >
          {profile.university ? profile.university.charAt(0).toUpperCase() : '?'}
        </div>
      </div>
    </header>
  )
}
