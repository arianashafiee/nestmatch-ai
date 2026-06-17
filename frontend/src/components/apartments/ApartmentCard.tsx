import { Link } from 'react-router-dom'
import { ScoreBadge } from '@/components/apartments/ScoreBadge'
import { ListingAddressDirections } from '@/components/apartments/ListingAddressDirections'
import { CommuteToCampusLabel } from '@/components/apartments/CommuteToCampusLabel'
import { cn } from '@/lib/utils'
import { isSampleListing } from '@/lib/kanban'
import type { Apartment } from '@/types/apartment'
import { listingTitleFromApartment, photoProxyUrl } from '@/types/apartment'

interface ApartmentCardProps {
  apartment: Apartment
  compact?: boolean
  pending?: boolean
}

export function ApartmentCard({ apartment, compact, pending }: ApartmentCardProps) {
  const analysis = apartment.analysis
  const score = apartment.compatibilityScore ?? analysis?.compatibility_score
  const title = listingTitleFromApartment(apartment)
  const rent = analysis?.rent_monthly ?? extractRentFromRawText(apartment.rawText)
  const sample = isSampleListing(apartment.rawText)

  const photos = apartment.photos ?? []
  const showPhoto = Boolean(photos[0]) && (!compact || pending)

  return (
    <div
      className={cn(
        'overflow-hidden rounded-xl border border-slate-200 bg-white transition-shadow hover:shadow-md',
        pending && 'border-indigo-200',
      )}
    >
      <Link to={`/board/${apartment.id}`} className={cn('block', compact && 'p-0')}>
      {showPhoto && (
        <img
          src={photoProxyUrl(photos[0])}
          alt=""
          className="h-32 w-full object-cover"
          onError={(e) => {
            const img = e.currentTarget
            if (img.dataset.fallbackApplied === '1') return
            img.dataset.fallbackApplied = '1'
            if (!img.src.includes(encodeURIComponent(photos[0]))) {
              img.src = photos[0]
            }
          }}
        />
      )}
      <div className={cn('p-4', compact && 'p-3')}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold text-slate-900">{title}</h3>
          {rent != null && (
            <p className="mt-0.5 text-sm font-medium text-indigo-600">
              ${rent.toLocaleString()}/mo
            </p>
          )}
          {!pending && analysis && (
            <CommuteToCampusLabel apartment={apartment} className="mt-1" />
          )}
          {!compact && analysis && (
            <p className="mt-2 line-clamp-2 text-xs text-slate-600">
              {analysis.pros?.[0] ?? analysis.cons?.[0]}
            </p>
          )}
        </div>
        {score != null && !pending && (
          <ScoreBadge score={score} size={compact ? 'sm' : 'md'} />
        )}
      </div>
      {pending && (
        <p className="mt-2 text-xs font-medium text-indigo-600">
          Analyzing compatibility…
        </p>
      )}
      {sample && (
        <span className="mt-2 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-800">
          Sample listing
        </span>
      )}
      {analysis && (analysis.red_flags?.length ?? 0) > 0 && !compact && (
        <p className="mt-2 text-xs text-red-600">
          {analysis.red_flags.length} red flag
          {analysis.red_flags.length === 1 ? '' : 's'}
        </p>
      )}
      </div>
      </Link>
      {analysis && (
        <div className="border-t border-slate-100 px-4 pb-3 pt-2">
          <ListingAddressDirections
            apartment={apartment}
            compact
            onPointerDown={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  )
}

function extractRentFromRawText(rawText: string): number | null {
  const match = rawText.match(/\$[\d,]+(?:\s*\/mo)?/i)
  if (!match) return null
  const value = Number(match[0].replace(/[^\d]/g, ''))
  return Number.isFinite(value) ? value : null
}
