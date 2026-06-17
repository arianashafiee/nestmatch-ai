import { useMemo, useState } from 'react'
import { KanbanCard } from '@/components/apartments/KanbanCard'
import { TourScheduleModal } from '@/components/apartments/TourScheduleModal'
import { cn } from '@/lib/utils'
import { KANBAN_COLUMNS } from '@/lib/kanban'
import type { Apartment, ApartmentStatus } from '@/types/apartment'

interface KanbanBoardProps {
  apartments: Apartment[]
  onMove: (id: number, status: ApartmentStatus) => void
  onScheduleTour: (id: number, tourAt: string) => Promise<void>
  onToggleFavorite: (id: number, isFavorite: boolean) => void
  onDelete: (id: number) => void
}

function sortInterested(apartments: Apartment[]): Apartment[] {
  return [...apartments].sort((a, b) => {
    if (a.isFavorite !== b.isFavorite) return a.isFavorite ? -1 : 1
    return (b.compatibilityScore ?? 0) - (a.compatibilityScore ?? 0)
  })
}

function needsTourDateTime(
  status: ApartmentStatus,
  apartment: Apartment | undefined,
): boolean {
  return status === 'tour_scheduled' && !apartment?.tourAt
}

export function KanbanBoard({
  apartments,
  onMove,
  onScheduleTour,
  onToggleFavorite,
  onDelete,
}: KanbanBoardProps) {
  const [draggingId, setDraggingId] = useState<number | null>(null)
  const [dropTarget, setDropTarget] = useState<ApartmentStatus | null>(null)
  const [scheduleListingId, setScheduleListingId] = useState<number | null>(
    null,
  )
  const [isScheduling, setIsScheduling] = useState(false)

  const boardApartments = apartments.filter(
    (a) => a.status !== 'pending' && a.analysis,
  )

  const scheduleListing = useMemo(
    () =>
      scheduleListingId == null
        ? null
        : boardApartments.find((a) => a.id === scheduleListingId) ?? null,
    [boardApartments, scheduleListingId],
  )

  const attemptMove = (id: number, status: ApartmentStatus) => {
    const apartment = boardApartments.find((a) => a.id === id)
    if (needsTourDateTime(status, apartment)) {
      setScheduleListingId(id)
      return
    }
    onMove(id, status)
  }

  const handleDrop = (status: ApartmentStatus) => {
    if (draggingId == null) return
    attemptMove(draggingId, status)
    setDraggingId(null)
    setDropTarget(null)
  }

  const handleConfirmSchedule = async (tourAt: string) => {
    if (scheduleListingId == null) return
    setIsScheduling(true)
    try {
      await onScheduleTour(scheduleListingId, tourAt)
      setScheduleListingId(null)
    } finally {
      setIsScheduling(false)
    }
  }

  return (
    <>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {KANBAN_COLUMNS.map((column) => {
          const columnItems = boardApartments.filter(
            (a) => a.status === column.key,
          )
          const items =
            column.key === 'interested'
              ? sortInterested(columnItems)
              : columnItems
          const isTarget = dropTarget === column.key

          return (
            <div
              key={column.key}
              className="min-w-[260px] flex-1"
              onDragOver={(e) => {
                e.preventDefault()
                setDropTarget(column.key)
              }}
              onDragLeave={() => setDropTarget(null)}
              onDrop={(e) => {
                e.preventDefault()
                handleDrop(column.key)
              }}
            >
              <div
                className={cn(
                  'rounded-xl border p-4 transition-colors',
                  isTarget
                    ? 'border-indigo-400 bg-indigo-50/80'
                    : 'border-slate-200 bg-slate-50',
                )}
              >
                <div className="mb-3">
                  <h3 className="text-sm font-semibold text-slate-800">
                    {column.label}
                    <span className="ml-1.5 font-normal text-slate-400">
                      ({items.length})
                    </span>
                  </h3>
                  <p className="text-xs text-slate-500">{column.description}</p>
                  {column.key === 'tour_scheduled' && (
                    <p className="mt-1 text-[10px] text-indigo-700">
                      Requires a tour date and time
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  {items.length === 0 ? (
                    <div
                      className={cn(
                        'rounded-lg border border-dashed py-10 text-center text-xs text-slate-400',
                        isTarget
                          ? 'border-indigo-300 bg-indigo-50 text-indigo-500'
                          : 'border-slate-200 bg-white',
                      )}
                    >
                      {isTarget ? 'Drop here' : 'Drag a card here'}
                    </div>
                  ) : (
                    items.map((apt) => (
                      <KanbanCard
                        key={apt.id}
                        apartment={apt}
                        onMove={attemptMove}
                        onRequestTourSchedule={() => setScheduleListingId(apt.id)}
                        onToggleFavorite={onToggleFavorite}
                        onDelete={onDelete}
                        onDragStart={setDraggingId}
                      />
                    ))
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <TourScheduleModal
        apartment={scheduleListing}
        isOpen={scheduleListingId != null}
        isSaving={isScheduling}
        onClose={() => setScheduleListingId(null)}
        onConfirm={handleConfirmSchedule}
      />
    </>
  )
}
