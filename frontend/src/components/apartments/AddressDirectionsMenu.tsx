import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { MapPin, Navigation } from 'lucide-react'
import { directionsAppsForRoute, openDirections } from '@/lib/directions'
import { cn } from '@/lib/utils'

interface AddressDirectionsMenuProps {
  /** Address shown on the card (selectable label). */
  address: string
  /** Route origin; omit to use the user's current location. */
  origin?: string
  menuTitle: string
  /** When true, directions require a campus/origin address from profile. */
  requireOrigin?: boolean
  missingOriginMessage?: string
  className?: string
  compact?: boolean
  onPointerDown?: (event: ReactMouseEvent) => void
}

export function AddressDirectionsMenu({
  address,
  origin,
  menuTitle,
  requireOrigin = false,
  missingOriginMessage,
  className,
  compact = false,
  onPointerDown,
}: AddressDirectionsMenuProps) {
  const [open, setOpen] = useState(false)
  const [menuStyle, setMenuStyle] = useState<{ top: number; left: number; width: number }>(
    { top: 0, left: 0, width: 240 },
  )
  const containerRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  const displayAddress = address.trim()
  const routeOrigin = origin?.trim() ?? ''
  const routeDestination = displayAddress
  const missingOrigin = requireOrigin && !routeOrigin
  const canRoute = Boolean(routeDestination) && !missingOrigin

  const updateMenuPosition = () => {
    const button = buttonRef.current
    if (!button) return
    const rect = button.getBoundingClientRect()
    setMenuStyle({
      top: rect.bottom + 4,
      left: rect.left,
      width: Math.max(rect.width, 240),
    })
  }

  useEffect(() => {
    if (!open) return

    updateMenuPosition()

    const handleClickOutside = (event: globalThis.MouseEvent) => {
      const target = event.target as Node
      if (
        containerRef.current?.contains(target) ||
        document.getElementById('address-directions-menu')?.contains(target)
      ) {
        return
      }
      setOpen(false)
    }

    const handleReposition = () => updateMenuPosition()

    document.addEventListener('mousedown', handleClickOutside)
    window.addEventListener('resize', handleReposition)
    window.addEventListener('scroll', handleReposition, true)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      window.removeEventListener('resize', handleReposition)
      window.removeEventListener('scroll', handleReposition, true)
    }
  }, [open])

  if (!displayAddress) return null

  const apps = directionsAppsForRoute({
    origin: routeOrigin || undefined,
    destination: routeDestination,
  })

  const menu = open && canRoute ? (
    <div
      id="address-directions-menu"
      role="menu"
      style={{
        position: 'fixed',
        top: menuStyle.top,
        left: menuStyle.left,
        width: menuStyle.width,
        zIndex: 9999,
      }}
      className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg"
    >
      <p className="border-b border-slate-100 px-3 py-2 text-[10px] font-medium uppercase tracking-wide text-slate-500">
        {menuTitle}
      </p>
      {routeOrigin && (
        <p className="border-b border-slate-100 px-3 py-2 text-[11px] text-slate-600">
          From: {routeOrigin}
        </p>
      )}
      <p className="border-b border-slate-100 px-3 py-2 text-[11px] text-slate-600">
        To: {routeDestination}
      </p>
      {apps.map((app) => (
        <button
          key={app.id}
          type="button"
          role="menuitem"
          className="flex w-full flex-col items-start px-3 py-2.5 text-left hover:bg-indigo-50"
          onClick={(event) => {
            event.stopPropagation()
            openDirections(
              app.id,
              routeDestination,
              routeOrigin || undefined,
            )
            setOpen(false)
          }}
        >
          <span className="text-sm font-medium text-slate-900">{app.label}</span>
          <span className="text-[11px] text-slate-500">{app.description}</span>
        </button>
      ))}
    </div>
  ) : null

  return (
    <div
      ref={containerRef}
      className={cn('relative', className)}
      draggable={false}
      onDragStart={(event) => event.preventDefault()}
    >
      <button
        ref={buttonRef}
        type="button"
        draggable={false}
        onPointerDown={(event) => {
          event.stopPropagation()
          onPointerDown?.(event)
        }}
        onClick={(event) => {
          event.stopPropagation()
          event.preventDefault()
          if (!canRoute) return
          setOpen((value) => !value)
        }}
        className={cn(
          'group flex w-full items-start gap-1 rounded-md text-left transition-colors',
          compact ? 'text-xs text-slate-500' : 'text-xs text-slate-600',
          canRoute
            ? 'cursor-pointer hover:bg-slate-50 hover:text-indigo-700'
            : 'cursor-default',
        )}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <MapPin className="mt-0.5 h-3 w-3 shrink-0 text-indigo-500" />
        <span
          className={cn(
            'min-w-0 flex-1 select-text',
            canRoute &&
              'underline decoration-dotted underline-offset-2 group-hover:decoration-solid',
            compact && 'truncate',
          )}
        >
          {displayAddress}
        </span>
        {canRoute && (
          <Navigation className="mt-0.5 h-3 w-3 shrink-0 opacity-60" />
        )}
      </button>

      {missingOrigin && missingOriginMessage && (
        <p className="mt-1 text-[10px] text-amber-700">
          {missingOriginMessage}{' '}
          <Link to="/profile" className="font-medium underline">
            Profile settings
          </Link>
        </p>
      )}

      {menu && createPortal(menu, document.body)}
    </div>
  )
}
