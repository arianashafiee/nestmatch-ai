import { ApartmentCard } from '@/components/apartments/ApartmentCard'
import { DeleteListingButton } from '@/components/apartments/DeleteListingButton'
import { FavoritesSection } from '@/components/apartments/FavoritesSection'
import { KanbanBoard } from '@/components/apartments/KanbanBoard'
import { ParsingOverlay } from '@/components/apartments/ParsingOverlay'
import { ApartmentCardSkeleton } from '@/components/ui/Skeleton'
import { useApartments } from '@/context/ApartmentsContext'

export function HuntingBoardPage() {
  const {
    apartments,
    isLoading,
    parsingIds,
    updateStatus,
    updateApartmentListing,
    toggleFavorite,
    deleteApartment,
  } = useApartments()

  const pending = apartments.filter(
    (a) => a.status === 'pending' || parsingIds.includes(a.id),
  )
  const parsed = apartments.filter((a) => a.analysis)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">
          Shortlist Board
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Drag cards between columns, star favorites, or delete any listing
          from your shortlist.
        </p>
      </div>

      {parsingIds.length > 0 && <ParsingOverlay count={parsingIds.length} />}

      {pending.length > 0 && parsingIds.length === 0 && (
        <section className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-4">
          <h3 className="text-sm font-semibold text-indigo-900">
            Awaiting analysis ({pending.length})
          </h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {pending.map((apt) => (
              <div key={apt.id} className="relative">
                <ApartmentCard apartment={apt} compact pending />
                <DeleteListingButton
                  apartment={apt}
                  onDelete={deleteApartment}
                  className="absolute right-2 top-2 bg-white/90 shadow-sm"
                  size="sm"
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {parsed.length > 0 && (
        <section>
          <h3 className="mb-3 text-sm font-semibold text-slate-700">
            Top Matches
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[...parsed]
              .sort(
                (a, b) =>
                  (b.compatibilityScore ?? 0) - (a.compatibilityScore ?? 0),
              )
              .slice(0, 3)
              .map((apt) => (
                <div key={apt.id} className="relative">
                  <ApartmentCard apartment={apt} />
                  <DeleteListingButton
                    apartment={apt}
                    onDelete={deleteApartment}
                    className="absolute right-2 top-2 bg-white/90 shadow-sm"
                    size="sm"
                  />
                </div>
              ))}
          </div>
        </section>
      )}

      {!isLoading && (
        <FavoritesSection
          apartments={apartments}
          onToggleFavorite={toggleFavorite}
          onDelete={deleteApartment}
        />
      )}

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <ApartmentCardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <KanbanBoard
          apartments={apartments}
          onMove={updateStatus}
          onScheduleTour={async (id, tourAt) => {
            await updateApartmentListing(id, {
              status: 'tour_scheduled',
              tourAt,
            })
          }}
          onToggleFavorite={toggleFavorite}
          onDelete={deleteApartment}
        />
      )}
    </div>
  )
}
