import { useState } from 'react'
import { KanbanCard } from '@/components/apartments/KanbanCard'
import { cn } from '@/lib/utils'
import { KANBAN_COLUMNS } from '@/lib/kanban'
import type { Apartment, ApartmentStatus } from '@/types/apartment'

interface KanbanBoardProps {
  apartments: Apartment[]
  onMove: (id: number, status: ApartmentStatus) => void
}

export function KanbanBoard({ apartments, onMove }: KanbanBoardProps) {
  const [draggingId, setDraggingId] = useState<number | null>(null)
  const [dropTarget, setDropTarget] = useState<ApartmentStatus | null>(null)

  const boardApartments = apartments.filter(
    (a) => a.status !== 'pending' && a.analysis,
  )

  const handleDrop = (status: ApartmentStatus) => {
    if (draggingId == null) return
    onMove(draggingId, status)
    setDraggingId(null)
    setDropTarget(null)
  }

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {KANBAN_COLUMNS.map((column) => {
        const items = boardApartments.filter((a) => a.status === column.key)
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
                      onMove={onMove}
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
  )
}
