import type { Apartment, TourNote } from '@/types/apartment'
import { listingTitleFromApartment } from '@/types/apartment'

export function formatTourDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatTourDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

export function formatTourTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function isTourPast(iso: string): boolean {
  return new Date(iso).getTime() < Date.now()
}

export function toursFromApartments(apartments: Apartment[]): Apartment[] {
  return apartments
    .filter((apt) => apt.tourAt)
    .sort(
      (a, b) =>
        new Date(a.tourAt!).getTime() - new Date(b.tourAt!).getTime(),
    )
}

export function getUpcomingTours(
  apartments: Apartment[],
  withinHours = 24,
): Apartment[] {
  const now = Date.now()
  const cutoff = now + withinHours * 60 * 60 * 1000
  return toursFromApartments(apartments).filter((apt) => {
    const tourTime = new Date(apt.tourAt!).getTime()
    return tourTime >= now && tourTime <= cutoff
  })
}

export function getNextTour(apartments: Apartment[]): Apartment | null {
  const upcoming = toursFromApartments(apartments).filter(
    (apt) => !isTourPast(apt.tourAt!),
  )
  return upcoming[0] ?? null
}

export function tourTitle(apartment: Apartment): string {
  return listingTitleFromApartment(apartment)
}

export function combineTourDateTime(date: string, time: string): string | null {
  if (!date || !time) return null
  const combined = new Date(`${date}T${time}`)
  if (Number.isNaN(combined.getTime())) return null
  return combined.toISOString()
}

export function splitTourDateTime(iso: string | null): {
  date: string
  time: string
} {
  if (!iso) return { date: '', time: '' }
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return { date: '', time: '' }
  const yyyy = date.getFullYear()
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  return { date: `${yyyy}-${mm}-${dd}`, time: `${hh}:${min}` }
}

export function createTourNote(text: string): TourNote {
  return {
    id: crypto.randomUUID(),
    text: text.trim(),
    createdAt: new Date().toISOString(),
  }
}

export function tourNotesToApi(notes: TourNote[]) {
  return notes.map((note) => ({
    id: note.id,
    text: note.text,
    created_at: note.createdAt,
  }))
}

export function reminderStorageKey(
  apartmentId: number,
  tourAt: string,
  window: '24h' | '2h' | '30m',
): string {
  return `nestmatch-tour-reminder-${apartmentId}-${tourAt}-${window}`
}

export function minutesUntilTour(iso: string): number {
  return Math.round((new Date(iso).getTime() - Date.now()) / 60000)
}

export function sameCalendarDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

export function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

export function addMonths(date: Date, delta: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + delta, 1)
}

export function calendarGridDays(month: Date): Date[] {
  const first = startOfMonth(month)
  const start = new Date(first)
  start.setDate(first.getDate() - first.getDay())
  return Array.from({ length: 42 }, (_, index) => {
    const day = new Date(start)
    day.setDate(start.getDate() + index)
    return day
  })
}
