import type { ApartmentStatus } from '@/types/apartment'

export const KANBAN_COLUMNS: {
  key: ApartmentStatus
  label: string
  description: string
}[] = [
  {
    key: 'interested',
    label: 'Interested',
    description: 'Newly parsed listings land here',
  },
  {
    key: 'contacted',
    label: 'Contacted',
    description: 'You reached out to the landlord',
  },
  {
    key: 'tour_scheduled',
    label: 'Tour Scheduled',
    description: 'A visit is on the calendar',
  },
  { key: 'applied', label: 'Applied', description: 'Application submitted' },
  {
    key: 'archived',
    label: 'Archived / Rejected',
    description: 'Ruled out or denied',
  },
]

export const STATUS_FLOW: ApartmentStatus[] = [
  'interested',
  'contacted',
  'tour_scheduled',
  'applied',
  'archived',
]

export function getNextStatus(
  current: ApartmentStatus,
): ApartmentStatus | null {
  const idx = STATUS_FLOW.indexOf(current)
  if (idx === -1 || idx >= STATUS_FLOW.length - 1) return null
  return STATUS_FLOW[idx + 1]
}

export function getPreviousStatus(
  current: ApartmentStatus,
): ApartmentStatus | null {
  const idx = STATUS_FLOW.indexOf(current)
  if (idx <= 0) return null
  return STATUS_FLOW[idx - 1]
}

const SAMPLE_MARKER =
  'Discovered via NestMatch campus search — sample listing for demo'

export function isSampleListing(rawText: string): boolean {
  return rawText.includes(SAMPLE_MARKER)
}
