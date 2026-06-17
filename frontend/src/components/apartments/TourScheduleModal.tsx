import { useEffect, useState } from 'react'
import { CalendarClock, Loader2, X } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { combineTourDateTime, splitTourDateTime } from '@/lib/tours'
import { listingTitleFromApartment } from '@/types/apartment'
import type { Apartment } from '@/types/apartment'

interface TourScheduleModalProps {
  apartment: Apartment | null
  isOpen: boolean
  isSaving?: boolean
  onClose: () => void
  onConfirm: (tourAt: string) => void
}

export function TourScheduleModal({
  apartment,
  isOpen,
  isSaving = false,
  onClose,
  onConfirm,
}: TourScheduleModalProps) {
  const initial = splitTourDateTime(apartment?.tourAt ?? null)
  const [tourDate, setTourDate] = useState(initial.date)
  const [tourTime, setTourTime] = useState(initial.time)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) return
    const split = splitTourDateTime(apartment?.tourAt ?? null)
    setTourDate(split.date)
    setTourTime(split.time)
    setError(null)
  }, [apartment?.id, apartment?.tourAt, isOpen])

  useEffect(() => {
    if (!isOpen) return
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = ''
    }
  }, [isOpen, onClose])

  if (!isOpen || !apartment) return null

  const handleSubmit = () => {
    const tourAt = combineTourDateTime(tourDate, tourTime)
    if (!tourAt) {
      setError('Pick a date and time for your tour.')
      return
    }
    if (new Date(tourAt).getTime() <= Date.now()) {
      setError('Tour time must be in the future.')
      return
    }
    setError(null)
    onConfirm(tourAt)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-schedule-title"
        className="relative z-10 w-full max-w-md rounded-t-2xl border border-slate-200 bg-white p-5 shadow-xl sm:rounded-2xl"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2
              id="tour-schedule-title"
              className="text-lg font-semibold text-slate-900"
            >
              Schedule tour
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {listingTitleFromApartment(apartment)}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <p className="mt-4 text-sm text-slate-600">
          Enter a tour date and time before moving this listing to Tour
          Scheduled.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Input
            id="kanban-tour-date"
            label="Tour date"
            type="date"
            value={tourDate}
            onChange={(e) => {
              setTourDate(e.target.value)
              setError(null)
            }}
          />
          <Input
            id="kanban-tour-time"
            label="Tour time"
            type="time"
            value={tourTime}
            onChange={(e) => {
              setTourTime(e.target.value)
              setError(null)
            }}
          />
        </div>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSaving}>
            {isSaving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <CalendarClock className="h-4 w-4" />
            )}
            Schedule & move
          </Button>
        </div>
      </div>
    </div>
  )
}
