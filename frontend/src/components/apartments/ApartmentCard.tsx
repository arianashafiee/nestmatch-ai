import { Link } from 'react-router-dom'
import { MapPin } from 'lucide-react'
import { ScoreBadge } from '@/components/apartments/ScoreBadge'
import { cn } from '@/lib/utils'
import { isSampleListing } from '@/lib/kanban'
import type { Apartment } from '@/types/apartment'
import { photoProxyUrl } from '@/types/apartment'

interface ApartmentCardProps {
  apartment: Apartment
  compact?: boolean
}

export function ApartmentCard({ apartment, compact }: ApartmentCardProps) {
  const analysis = apartment.analysis
  const score = apartment.compatibilityScore ?? analysis?.compatibility_score
  const title = apartment.title ?? analysis?.title ?? 'Untitled listing'
  const rent = analysis?.rent_monthly
  const sample = isSampleListing(apartment.rawText)

  const photos = apartment.photos ?? []

  return (
    <Link
      to={`/board/${apartment.id}`}
      className={cn(
        'block overflow-hidden rounded-xl border border-slate-200 bg-white transition-shadow hover:shadow-md',
        compact && 'p-0',
      )}
    >
      {photos[0] && !compact && (
        <img
          src={photoProxyUrl(photos[0])}
          alt=""
          className="h-32 w-full object-cover"
          onError={(e) => {
            e.currentTarget.src = photos[0]
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
          {analysis?.location && (
            <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
              <MapPin className="h-3 w-3 shrink-0" />
              <span className="truncate">{analysis.location}</span>
            </p>
          )}
          {!compact && analysis && (
            <p className="mt-2 line-clamp-2 text-xs text-slate-600">
              {analysis.pros?.[0] ?? analysis.cons?.[0]}
            </p>
          )}
        </div>
        {score != null && <ScoreBadge score={score} size={compact ? 'sm' : 'md'} />}
      </div>
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
  )
}
