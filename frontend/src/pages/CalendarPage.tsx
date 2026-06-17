import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Clock } from 'lucide-react'
import { TourAddressDirections } from '@/components/apartments/TourAddressDirections'
import { Button } from '@/components/ui/Button'
import { useApartments } from '@/context/ApartmentsContext'
import {
  addMonths,
  calendarGridDays,
  formatTourDateTime,
  formatTourTime,
  isTourPast,
  sameCalendarDay,
  startOfMonth,
  tourTitle,
  toursFromApartments,
} from '@/lib/tours'
import { cn } from '@/lib/utils'
import type { Apartment } from '@/types/apartment'
import { mapLocationForApartment } from '@/types/apartment'

function tourAddress(apartment: Apartment): string {
  return mapLocationForApartment(apartment)
}

export function CalendarPage() {
  const { apartments } = useApartments()
  const [visibleMonth, setVisibleMonth] = useState(() => startOfMonth(new Date()))
  const [selectedDay, setSelectedDay] = useState<Date>(() => new Date())

  const tours = useMemo(() => toursFromApartments(apartments), [apartments])
  const upcomingTours = useMemo(
    () => tours.filter((apt) => apt.tourAt && !isTourPast(apt.tourAt)),
    [tours],
  )
  const pastTours = useMemo(
    () => tours.filter((apt) => apt.tourAt && isTourPast(apt.tourAt)),
    [tours],
  )

  const gridDays = useMemo(
    () => calendarGridDays(visibleMonth),
    [visibleMonth],
  )

  const toursOnDay = (day: Date): Apartment[] =>
    tours.filter(
      (apt) => apt.tourAt && sameCalendarDay(new Date(apt.tourAt), day),
    )

  const selectedTours = toursOnDay(selectedDay)
  const monthLabel = visibleMonth.toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  })

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Tour Calendar</h2>
        <p className="mt-1 text-sm text-slate-500">
          All scheduled property tours. NestMatch reminds you as each tour
          approaches.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">{monthLabel}</h3>
            <div className="flex gap-1">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setVisibleMonth((month) => addMonths(month, -1))}
                aria-label="Previous month"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  const today = startOfMonth(new Date())
                  setVisibleMonth(today)
                  setSelectedDay(new Date())
                }}
              >
                Today
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setVisibleMonth((month) => addMonths(month, 1))}
                aria-label="Next month"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-slate-500">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
              <div key={day} className="py-2">
                {day}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1">
            {gridDays.map((day) => {
              const inMonth = day.getMonth() === visibleMonth.getMonth()
              const dayTours = toursOnDay(day)
              const isSelected = sameCalendarDay(day, selectedDay)
              const isToday = sameCalendarDay(day, new Date())

              return (
                <button
                  key={day.toISOString()}
                  type="button"
                  onClick={() => setSelectedDay(day)}
                  className={cn(
                    'min-h-[72px] rounded-lg border p-1.5 text-left transition-colors',
                    inMonth ? 'bg-white' : 'bg-slate-50 text-slate-400',
                    isSelected
                      ? 'border-indigo-400 ring-2 ring-indigo-100'
                      : 'border-slate-100 hover:border-slate-200',
                  )}
                >
                  <span
                    className={cn(
                      'inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium',
                      isToday && 'bg-indigo-600 text-white',
                    )}
                  >
                    {day.getDate()}
                  </span>
                  {dayTours.length > 0 && (
                    <div className="mt-1 space-y-0.5">
                      {dayTours.slice(0, 2).map((apt) => (
                        <span
                          key={apt.id}
                          className="block truncate rounded bg-indigo-50 px-1 py-0.5 text-[10px] font-medium text-indigo-700"
                        >
                          {formatTourTime(apt.tourAt!)}
                        </span>
                      ))}
                      {dayTours.length > 2 && (
                        <span className="block text-[10px] text-slate-500">
                          +{dayTours.length - 2} more
                        </span>
                      )}
                    </div>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h3 className="font-semibold text-slate-900">
              {selectedDay.toLocaleDateString(undefined, {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
              })}
            </h3>
            {selectedTours.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">No tours scheduled.</p>
            ) : (
              <ul className="mt-3 space-y-3">
                {selectedTours.map((apt) => (
                  <li
                    key={apt.id}
                    className="rounded-lg border border-indigo-100 bg-indigo-50/40 p-3"
                  >
                    <Link
                      to={`/board/${apt.id}`}
                      className="font-medium text-indigo-800 hover:underline"
                    >
                      {tourTitle(apt)}
                    </Link>
                    <p className="mt-1 flex items-center gap-1 text-xs text-slate-600">
                      <Clock className="h-3.5 w-3.5" />
                      {formatTourDateTime(apt.tourAt!)}
                    </p>
                    <TourAddressDirections address={tourAddress(apt)} />
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h3 className="font-semibold text-slate-900">Upcoming tours</h3>
            {upcomingTours.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">
                Schedule a tour from a listing&apos;s progress steps to see it
                here.
              </p>
            ) : (
              <ul className="mt-3 space-y-3">
                {upcomingTours.map((apt) => (
                  <li key={apt.id} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                    <Link
                      to={`/board/${apt.id}`}
                      className="text-sm font-medium text-indigo-700 hover:underline"
                    >
                      {tourTitle(apt)}
                    </Link>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {formatTourDateTime(apt.tourAt!)}
                    </p>
                    <TourAddressDirections address={tourAddress(apt)} />
                  </li>
                ))}
              </ul>
            )}
          </div>

          {pastTours.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h3 className="font-semibold text-slate-900">Past tours</h3>
              <ul className="mt-3 space-y-2">
                {pastTours.slice(0, 5).map((apt) => (
                  <li key={apt.id}>
                    <Link
                      to={`/board/${apt.id}`}
                      className="text-sm text-slate-700 hover:text-indigo-700 hover:underline"
                    >
                      {tourTitle(apt)}
                    </Link>
                    <p className="text-xs text-slate-400">
                      {formatTourDateTime(apt.tourAt!)}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
