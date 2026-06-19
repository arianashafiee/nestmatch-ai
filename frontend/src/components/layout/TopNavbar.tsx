import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Bell, LogOut, Menu, Plus, UserCircle, X } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useApartments } from '@/context/ApartmentsContext'
import { useAuth } from '@/context/AuthContext'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { cn } from '@/lib/utils'

const pageTitles: Record<string, string> = {
  '/': 'Hunting Board',
  '/profile': 'Student Profile',
  '/calendar': 'Tour Calendar',
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
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { profile, isProfileComplete } = useStudentProfile()
  const {
    openAddModal,
    isListingSearchInProgress,
    hasUnreadListingSearch,
  } = useApartments()
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false)
  const profileMenuRef = useRef<HTMLDivElement>(null)
  const title = getPageTitle(location.pathname)

  useEffect(() => {
    if (!isProfileMenuOpen) return

    const handleClickOutside = (event: MouseEvent) => {
      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(event.target as Node)
      ) {
        setIsProfileMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isProfileMenuOpen])

  useEffect(() => {
    setIsProfileMenuOpen(false)
  }, [location.pathname])

  const handleSignOut = () => {
    setIsProfileMenuOpen(false)
    logout()
    navigate('/login')
  }

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
          className="relative inline-flex"
          aria-label="Find Apartments"
        >
          <Plus className="h-4 w-4" />
          <span className="hidden sm:inline">Find Apartments</span>
          {(isListingSearchInProgress || hasUnreadListingSearch) && (
            <span
              className={cn(
                'absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border-2 border-white',
                isListingSearchInProgress
                  ? 'animate-pulse bg-indigo-400'
                  : 'bg-emerald-500',
              )}
              aria-hidden
            />
          )}
        </Button>

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

        <div className="relative" ref={profileMenuRef}>
          <button
            type="button"
            onClick={() => setIsProfileMenuOpen((open) => !open)}
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold transition-colors hover:ring-2 hover:ring-indigo-200 focus:outline-none focus:ring-2 focus:ring-indigo-500',
              isProfileComplete
                ? 'bg-indigo-100 text-indigo-700'
                : 'bg-slate-100 text-slate-500',
              isProfileMenuOpen && 'ring-2 ring-indigo-500',
            )}
            aria-label="Profile menu"
            aria-expanded={isProfileMenuOpen}
            aria-haspopup="menu"
          >
            {profile.university ? profile.university.charAt(0).toUpperCase() : '?'}
          </button>

          {isProfileMenuOpen && (
            <div
              role="menu"
              className="absolute right-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-lg"
            >
              {user && (
                <p className="truncate border-b border-slate-100 px-4 py-2.5 text-xs text-slate-500">
                  {user.email}
                </p>
              )}
              <Link
                to="/profile"
                role="menuitem"
                onClick={() => setIsProfileMenuOpen(false)}
                className="flex items-center gap-2 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50"
              >
                <UserCircle className="h-4 w-4 text-slate-500" />
                Profile settings
              </Link>
              <button
                type="button"
                role="menuitem"
                onClick={handleSignOut}
                className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50"
              >
                <LogOut className="h-4 w-4 text-slate-500" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
