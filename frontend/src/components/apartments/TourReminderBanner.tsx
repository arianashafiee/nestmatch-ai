import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Bell, CalendarClock } from 'lucide-react'
import { useApartments } from '@/context/ApartmentsContext'
import { useToast } from '@/context/ToastContext'
import {
  formatTourDateTime,
  getUpcomingTours,
  minutesUntilTour,
  reminderStorageKey,
  tourTitle,
} from '@/lib/tours'

const REMINDER_WINDOWS: {
  key: '24h' | '2h' | '30m'
  minMinutes: number
  maxMinutes: number
}[] = [
  { key: '24h', minMinutes: 120, maxMinutes: 24 * 60 },
  { key: '2h', minMinutes: 30, maxMinutes: 120 },
  { key: '30m', minMinutes: 0, maxMinutes: 30 },
]

export function TourReminderBanner() {
  const { apartments } = useApartments()
  const { showToast } = useToast()
  const upcoming = getUpcomingTours(apartments, 24)
  const nextTour = upcoming[0]

  useEffect(() => {
    const checkReminders = () => {
      for (const apt of getUpcomingTours(apartments, 24)) {
        if (!apt.tourAt) continue
        const minutes = minutesUntilTour(apt.tourAt)
        for (const window of REMINDER_WINDOWS) {
          if (minutes > window.maxMinutes || minutes < window.minMinutes) continue
          const storageKey = reminderStorageKey(apt.id, apt.tourAt, window.key)
          if (localStorage.getItem(storageKey)) continue
          localStorage.setItem(storageKey, '1')
          showToast(
            window.key === '30m'
              ? `Tour in ${minutes} min — ${tourTitle(apt)}`
              : window.key === '2h'
                ? `Tour in about 2 hours — ${tourTitle(apt)}`
                : `Upcoming tour tomorrow — ${tourTitle(apt)} at ${formatTourDateTime(apt.tourAt)}`,
            'info',
          )
        }
      }
    }

    checkReminders()
    const interval = window.setInterval(checkReminders, 60_000)
    return () => window.clearInterval(interval)
  }, [apartments, showToast])

  if (!nextTour?.tourAt) return null

  const minutes = minutesUntilTour(nextTour.tourAt)
  if (minutes < 0 || minutes > 24 * 60) return null

  return (
    <div className="border-b border-indigo-100 bg-indigo-50 px-4 py-2.5 md:px-6">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-indigo-900">
        <p className="flex items-center gap-2">
          <Bell className="h-4 w-4 shrink-0" />
          <span>
            <strong>{tourTitle(nextTour)}</strong> tour{' '}
            {minutes <= 120
              ? `in ${minutes} min`
              : `on ${formatTourDateTime(nextTour.tourAt)}`}
          </span>
        </p>
        <Link
          to="/calendar"
          className="inline-flex items-center gap-1 font-medium text-indigo-700 hover:underline"
        >
          <CalendarClock className="h-4 w-4" />
          View calendar
        </Link>
      </div>
    </div>
  )
}
