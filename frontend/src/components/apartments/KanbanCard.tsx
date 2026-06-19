import { Link } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  GripVertical,
  Star,
  Trash2,
} from 'lucide-react'
import { ScoreBadge } from '@/components/apartments/ScoreBadge'
import { ListingAddressDirections } from '@/components/apartments/ListingAddressDirections'
import { CommuteToCampusLabel } from '@/components/apartments/CommuteToCampusLabel'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { formatRentForProfile } from '@/lib/rentSharing'
import { formatTourDateTime } from '@/lib/tours'
import { confirmDeleteListing } from '@/lib/listingActions'
import { cn } from '@/lib/utils'
import {
  getNextStatus,
  getPreviousStatus,
  isSampleListing,
} from '@/lib/kanban'
import type { Apartment, ApartmentStatus } from '@/types/apartment'
import { KANBAN_COLUMNS } from '@/lib/kanban'

interface KanbanCardProps {
  apartment: Apartment
  onMove: (id: number, status: ApartmentStatus) => void
  onRequestTourSchedule: () => void
  onToggleFavorite: (id: number, isFavorite: boolean) => void
  onDelete: (id: number) => void
  onDragStart: (id: number) => void
}

const statusLabels = Object.fromEntries(
  KANBAN_COLUMNS.map((c) => [c.key, c.label]),
) as Record<ApartmentStatus, string>

export function KanbanCard({
  apartment,
  onMove,
  onRequestTourSchedule,
  onToggleFavorite,
  onDelete,
  onDragStart,
}: KanbanCardProps) {
  const { profile } = useStudentProfile()
  const analysis = apartment.analysis
  const score = apartment.compatibilityScore ?? analysis?.compatibility_score
  const title = apartment.title ?? analysis?.title ?? 'Untitled listing'
  const rent = analysis?.rent_monthly
  const sample = isSampleListing(apartment.rawText)
  const prev = getPreviousStatus(apartment.status)
  const next = getNextStatus(apartment.status)
  const showFavorite = apartment.status === 'interested'

  const handleDelete = () => {
    if (!confirmDeleteListing(apartment)) return
    onDelete(apartment.id)
  }

  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('apartmentId', String(apartment.id))
        e.dataTransfer.effectAllowed = 'move'
        onDragStart(apartment.id)
      }}
      className={cn(
        'group rounded-lg border bg-white shadow-sm transition-shadow hover:shadow-md',
        apartment.isFavorite && showFavorite
          ? 'border-amber-200 ring-1 ring-amber-100'
          : 'border-slate-200',
      )}
    >
      <div className="flex items-start gap-1 p-3">
        <GripVertical className="mt-0.5 h-4 w-4 shrink-0 cursor-grab text-slate-300 active:cursor-grabbing" />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <Link
              to={`/board/${apartment.id}`}
              className="min-w-0 flex-1"
              onClick={(e) => e.stopPropagation()}
            >
              <h4 className="truncate text-sm font-semibold text-slate-900 hover:text-indigo-700">
                {title}
              </h4>
            </Link>
            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                onClick={handleDelete}
                className="rounded p-1 text-slate-300 transition-colors hover:bg-red-50 hover:text-red-600"
                aria-label={`Delete ${title}`}
              >
                <Trash2 className="h-4 w-4" />
              </button>
              {showFavorite && (
                <button
                  type="button"
                  onClick={() =>
                    onToggleFavorite(apartment.id, !apartment.isFavorite)
                  }
                  className={cn(
                    'rounded p-1 transition-colors',
                    apartment.isFavorite
                      ? 'text-amber-500 hover:text-amber-600'
                      : 'text-slate-300 hover:text-amber-500',
                  )}
                  aria-label={
                    apartment.isFavorite
                      ? 'Remove from favorites'
                      : 'Add to favorites'
                  }
                >
                  <Star
                    className={cn(
                      'h-4 w-4',
                      apartment.isFavorite && 'fill-current',
                    )}
                  />
                </button>
              )}
              {score != null && (
                <ScoreBadge score={score} size="sm" className="h-9 w-9 text-xs" />
              )}
            </div>
          </div>
          {rent != null && (
            <p className="mt-0.5 text-xs font-medium text-indigo-600">
              {formatRentForProfile(rent, profile, apartment.rawText)}
            </p>
          )}
          <CommuteToCampusLabel apartment={apartment} className="mt-1" />
          {analysis && (
            <ListingAddressDirections
              apartment={apartment}
              compact
              className="mt-1"
              onPointerDown={(e) => e.stopPropagation()}
            />
          )}
          {apartment.tourAt && (
            <p className="mt-1 text-[10px] font-medium text-indigo-700">
              Tour: {formatTourDateTime(apartment.tourAt)}
            </p>
          )}
          {sample && (
            <span className="mt-2 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-800">
              Sample listing
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-slate-100 px-2 py-1.5">
        <button
          type="button"
          disabled={!prev}
          onClick={() => prev && onMove(apartment.id, prev)}
          className={cn(
            'rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700',
            !prev && 'invisible',
          )}
          aria-label="Move to previous stage"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <Link
          to={`/board/${apartment.id}`}
          className="text-[10px] font-medium text-indigo-600 hover:text-indigo-800"
        >
          View details
        </Link>
        <button
          type="button"
          disabled={!next}
          onClick={() => {
            if (!next) return
            if (next === 'tour_scheduled' && !apartment.tourAt) {
              onRequestTourSchedule()
              return
            }
            onMove(apartment.id, next)
          }}
          className={cn(
            'rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700',
            !next && 'invisible',
          )}
          aria-label={
            next ? `Move to ${statusLabels[next]}` : 'No next stage'
          }
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
