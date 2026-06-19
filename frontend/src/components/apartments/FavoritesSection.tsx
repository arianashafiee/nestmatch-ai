import { Link } from 'react-router-dom'
import { Star, Trash2 } from 'lucide-react'
import { ScoreBadge } from '@/components/apartments/ScoreBadge'
import { ListingAddressDirections } from '@/components/apartments/ListingAddressDirections'
import { CommuteToCampusLabel } from '@/components/apartments/CommuteToCampusLabel'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { formatRentForProfile } from '@/lib/rentSharing'
import { confirmDeleteListing } from '@/lib/listingActions'
import { cn } from '@/lib/utils'
import { KANBAN_COLUMNS } from '@/lib/kanban'
import type { Apartment } from '@/types/apartment'

interface FavoritesSectionProps {
  apartments: Apartment[]
  onToggleFavorite: (id: number, isFavorite: boolean) => void
  onDelete: (id: number) => void
}

const statusLabels = Object.fromEntries(
  KANBAN_COLUMNS.map((c) => [c.key, c.label]),
) as Record<string, string>

export function FavoritesSection({
  apartments,
  onToggleFavorite,
  onDelete,
}: FavoritesSectionProps) {
  const { profile } = useStudentProfile()
  const favorites = apartments
    .filter((a) => a.isFavorite && a.analysis && a.status !== 'pending')
    .sort(
      (a, b) =>
        (b.compatibilityScore ?? b.analysis?.compatibility_score ?? 0) -
        (a.compatibilityScore ?? a.analysis?.compatibility_score ?? 0),
    )

  const handleDelete = (apartment: Apartment) => {
    if (!confirmDeleteListing(apartment)) return
    onDelete(apartment.id)
  }

  return (
    <section className="rounded-xl border border-amber-200 bg-amber-50/40 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
        <h3 className="text-sm font-semibold text-slate-900">
          Favorites
          <span className="ml-1.5 font-normal text-slate-400">
            ({favorites.length})
          </span>
        </h3>
      </div>

      {favorites.length === 0 ? (
        <p className="text-sm text-slate-500">
          Star listings in Interested to save them here.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {favorites.map((apt) => {
            const analysis = apt.analysis
            const score =
              apt.compatibilityScore ?? analysis?.compatibility_score
            const title = apt.title ?? analysis?.title ?? 'Untitled listing'
            const rent = analysis?.rent_monthly

            return (
              <div
                key={apt.id}
                className="rounded-lg border border-amber-200 bg-white shadow-sm"
              >
                <div className="flex items-start gap-2 p-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <Link
                        to={`/board/${apt.id}`}
                        className="min-w-0 flex-1"
                      >
                        <h4 className="truncate text-sm font-semibold text-slate-900 hover:text-indigo-700">
                          {title}
                        </h4>
                      </Link>
                      {score != null && (
                        <ScoreBadge
                          score={score}
                          size="sm"
                          className="h-8 w-8 shrink-0 text-xs"
                        />
                      )}
                    </div>
                    {rent != null && (
                      <p className="mt-0.5 text-xs font-medium text-indigo-600">
                        {formatRentForProfile(rent, profile, apt.rawText)}
                      </p>
                    )}
                    <CommuteToCampusLabel apartment={apt} className="mt-1" />
                    <ListingAddressDirections
                      apartment={apt}
                      compact
                      className="mt-1"
                    />
                    <span className="mt-2 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                      {statusLabels[apt.status] ?? apt.status}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between border-t border-amber-100 px-2 py-1.5">
                  <button
                    type="button"
                    onClick={() => onToggleFavorite(apt.id, false)}
                    className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-50"
                  >
                    <Star className="h-3.5 w-3.5 fill-current" />
                    Unfavorite
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(apt)}
                    className={cn(
                      'flex items-center gap-1 rounded px-2 py-1 text-xs font-medium',
                      'text-red-600 hover:bg-red-50',
                    )}
                    aria-label={`Delete ${title}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
