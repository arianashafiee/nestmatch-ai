import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CheckCircle2,
  ExternalLink,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
} from 'lucide-react'
import { ScoreBadge } from '@/components/apartments/ScoreBadge'
import { Button } from '@/components/ui/Button'
import {
  findApartmentByListingUrl,
  isApartmentAnalyzed,
  isListingEligibleForAnalysis,
  sortSearchResultsByScore,
} from '@/lib/listingActions'
import { useApartments } from '@/context/ApartmentsContext'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { useToast } from '@/context/ToastContext'
import { cn } from '@/lib/utils'
import { commuteLabelFromDistance } from '@/lib/commute'
import type { Apartment, SearchListingResult } from '@/types/apartment'
import { normalizeApartment, photoProxyUrl } from '@/types/apartment'

const SOURCE_LABELS: Record<string, string> = {
  jhu_housing: 'JHU Off-Campus Housing',
  'apartments.com': 'Apartments.com',
  'rent.com': 'Rent.com',
  'zillow.com': 'Zillow',
  craigslist: 'Craigslist',
  'realtor.com': 'Realtor.com',
}

interface DiscoverListingsProps {
  onAdded?: () => void
}

export function DiscoverListings({ onAdded }: DiscoverListingsProps) {
  const { profile, isProfileComplete } = useStudentProfile()
  const {
    apartments,
    addApartment,
    parseApartment,
    isSubmitting,
    parsingIds,
    listingSearch,
    isListingSearchInProgress,
    isProfileStaleForSearch,
    searchListingsNearCampus,
    updateListingSearchResults,
  } = useApartments()
  const { showToast } = useToast()

  const [isAnalyzingAll, setIsAnalyzingAll] = useState(false)
  const [analyzeAllProgress, setAnalyzeAllProgress] = useState({
    current: 0,
    total: 0,
  })
  const [addingUrl, setAddingUrl] = useState<string | null>(null)

  const area = profile.campusLocation || profile.university

  const results = useMemo(
    () =>
      listingSearch
        ? sortSearchResultsByScore(listingSearch.results, apartments)
        : [],
    [apartments, listingSearch],
  )

  const sourcesSearched = listingSearch?.sourcesSearched ?? []
  const searchErrors = listingSearch?.searchErrors ?? {}
  const searchArea = listingSearch?.searchArea ?? ''
  const searchMeta = listingSearch?.searchMeta ?? null

  const eligibleListings = useMemo(
    () =>
      results.filter((listing) =>
        isListingEligibleForAnalysis(apartments, listing.url, parsingIds),
      ),
    [apartments, parsingIds, results],
  )

  const analyzeListing = async (
    listing: SearchListingResult,
    knownApartments: Apartment[],
  ): Promise<Apartment | null> => {
    const existing = findApartmentByListingUrl(knownApartments, listing.url)
    if (existing && isApartmentAnalyzed(existing)) return existing

    if (existing) {
      return parseApartment(existing.id, listing.rawText)
    }

    return addApartment(listing.rawText, {
      sourceUrl: listing.url,
      photos: listing.photos,
      sourceSite: listing.sourceSite,
    })
  }

  const upsertLocalApartment = (
    list: Apartment[],
    updated: Apartment,
  ): Apartment[] => {
    const normalized = normalizeApartment(updated)
    const idx = list.findIndex((a) => a.id === normalized.id)
    if (idx === -1) return [normalized, ...list]
    const next = [...list]
    next[idx] = normalized
    return next
  }

  const handleSearch = () => {
    if (!isProfileComplete) return
    void searchListingsNearCampus({ force: true })
  }

  const handleAdd = async (listing: SearchListingResult) => {
    const existing = findApartmentByListingUrl(apartments, listing.url)
    if (existing && isApartmentAnalyzed(existing)) return

    setAddingUrl(listing.url)
    const parsed = await analyzeListing(listing, apartments)
    setAddingUrl(null)
    if (parsed) {
      updateListingSearchResults(
        sortSearchResultsByScore(
          results,
          upsertLocalApartment(apartments, parsed),
        ),
      )
    }
    onAdded?.()
  }

  const handleAnalyzeAll = async () => {
    if (eligibleListings.length === 0) return

    setIsAnalyzingAll(true)
    setAnalyzeAllProgress({ current: 0, total: eligibleListings.length })

    let localApartments = apartments
    let analyzedCount = 0

    try {
      for (let index = 0; index < eligibleListings.length; index++) {
        const listing = eligibleListings[index]
        setAnalyzeAllProgress({
          current: index + 1,
          total: eligibleListings.length,
        })
        setAddingUrl(listing.url)

        const parsed = await analyzeListing(listing, localApartments)
        if (parsed) {
          localApartments = upsertLocalApartment(localApartments, parsed)
          if (isApartmentAnalyzed(parsed)) analyzedCount += 1
        }
      }

      updateListingSearchResults(
        sortSearchResultsByScore(results, localApartments),
      )
      showToast(
        analyzedCount === 1
          ? 'Analyzed 1 listing — results sorted by compatibility score'
          : `Analyzed ${analyzedCount} listings — results sorted by compatibility score`,
        'success',
      )
      onAdded?.()
    } catch (err) {
      showToast(
        err instanceof Error ? err.message : 'Batch analysis failed',
        'error',
      )
    } finally {
      setAddingUrl(null)
      setIsAnalyzingAll(false)
      setAnalyzeAllProgress({ current: 0, total: 0 })
    }
  }

  const hasCachedResults = results.length > 0

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
        <p className="font-medium">Automatic search across rental sites</p>
        <p className="mt-1 text-indigo-800">
          NestMatch searches <strong>JHU Off-Campus Housing</strong>,{' '}
          <strong>Apartments.com</strong>, <strong>Rent.com</strong>,{' '}
          <strong>Zillow</strong>, <strong>Craigslist</strong>, and{' '}
          <strong>Realtor.com</strong> near your campus address. JHU portal
          listings use each property&apos;s street address; other sites are
          filtered by your max {profile.commuteMode} commute (
          {profile.maxCommuteMinutes} min) and budget (${profile.maxRent}/mo).
          With <strong>OpenAI</strong> configured, results are also AI-ranked
          and summarized for your profile.
        </p>
        {hasCachedResults && (
          <p className="mt-2 text-xs text-indigo-700">
            Results stay saved when you close this window. You can leave while a
            search runs and come back to view listings.
          </p>
        )}
      </div>

      {!isProfileComplete ? (
        <p className="text-sm text-amber-700">
          Complete your profile with campus location and budget to search.
        </p>
      ) : (
        <Button
          onClick={handleSearch}
          disabled={isListingSearchInProgress || isSubmitting}
        >
          {isListingSearchInProgress ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Searching near {area}...
            </>
          ) : isProfileStaleForSearch && hasCachedResults ? (
            <>
              <RefreshCw className="h-4 w-4" />
              Refresh for updated profile
            </>
          ) : hasCachedResults ? (
            <>
              <Search className="h-4 w-4" />
              Search again
            </>
          ) : (
            <>
              <Search className="h-4 w-4" />
              Search all sites near campus
            </>
          )}
        </Button>
      )}

      {isProfileStaleForSearch && hasCachedResults && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-medium">Your profile changed since this search</p>
          <p className="mt-1 text-xs text-amber-800">
            Showing your last results below. Refresh the search to update
            commute filtering, budget, and AI ranking for your new settings.
          </p>
        </div>
      )}

      {isListingSearchInProgress && hasCachedResults && (
        <p className="text-xs font-medium text-indigo-700">
          Search in progress — previous results stay visible until the new search
          finishes.
        </p>
      )}

      {searchMeta?.aiRanked && !isProfileStaleForSearch && (
        <p className="text-xs font-medium text-indigo-700">
          Results ranked by OpenAI based on your budget, commute, and
          preferences.
        </p>
      )}

      {searchMeta && searchArea && (
        <p className="text-xs text-slate-600">
          Searching rentals in <strong>{searchArea}</strong>
          {searchMeta.campusGeocoded
            ? ` within ${searchMeta.maxCommuteMinutes} min ${searchMeta.commuteMode} of your campus address.`
            : ' (could not geocode campus — showing city-wide results).'}
        </p>
      )}

      {Object.keys(searchErrors).length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-medium">Search notes</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
            {Object.entries(searchErrors).map(([source, message]) => (
              <li key={source}>
                <strong>{SOURCE_LABELS[source] ?? source}:</strong> {message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {sourcesSearched.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {sourcesSearched.map((source) => (
            <span
              key={source}
              className={cn(
                'rounded-full px-2.5 py-1 text-xs font-medium',
                searchErrors[source]
                  ? 'bg-red-50 text-red-700'
                  : 'bg-emerald-50 text-emerald-700',
              )}
            >
              {SOURCE_LABELS[source] ?? source}
              {searchErrors[source]
                ? ' — limited'
                : results.some((r) => r.sourceSite === source)
                  ? ' ✓'
                  : ' — no results'}
            </span>
          ))}
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {results.length} real listings found
            </p>
            {eligibleListings.length > 0 ? (
              <Button
                size="sm"
                onClick={handleAnalyzeAll}
                disabled={
                  isAnalyzingAll ||
                  isListingSearchInProgress ||
                  isSubmitting ||
                  Boolean(addingUrl && !isAnalyzingAll)
                }
              >
                {isAnalyzingAll ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Analyzing {analyzeAllProgress.current} of{' '}
                    {analyzeAllProgress.total}...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Analyze all ({eligibleListings.length})
                  </>
                )}
              </Button>
            ) : (
              <p className="text-xs font-medium text-emerald-700">
                All listings analyzed — sorted by compatibility score
              </p>
            )}
          </div>
          {results.map((listing) => {
            const existing = findApartmentByListingUrl(apartments, listing.url)
            const isAnalyzed = existing ? isApartmentAnalyzed(existing) : false
            const isAnalyzing = Boolean(
              existing &&
                !isAnalyzed &&
                (parsingIds.includes(existing.id) ||
                  existing.status === 'pending'),
            )
            const score =
              existing?.compatibilityScore ??
              existing?.analysis?.compatibility_score

            return (
              <div
                key={listing.url}
                className={cn(
                  'overflow-hidden rounded-xl border bg-white',
                  isAnalyzed
                    ? 'border-emerald-200 bg-emerald-50/30'
                    : 'border-slate-200',
                )}
              >
                <div className="flex flex-col sm:flex-row">
                  {listing.photos[0] ? (
                    <img
                      src={photoProxyUrl(listing.photos[0])}
                      alt=""
                      className="h-36 w-full shrink-0 object-cover sm:h-auto sm:w-40"
                      onError={(e) => {
                        const img = e.currentTarget
                        if (img.dataset.fallbackApplied === '1') return
                        img.dataset.fallbackApplied = '1'
                        if (
                          !img.src.includes(
                            encodeURIComponent(listing.photos[0]),
                          )
                        ) {
                          img.src = listing.photos[0]
                        }
                      }}
                    />
                  ) : (
                    <div className="flex h-28 w-full shrink-0 items-center justify-center bg-slate-100 sm:w-40">
                      <span className="text-xs text-slate-400">
                        Photo on add
                      </span>
                    </div>
                  )}
                  <div className="flex flex-1 items-start justify-between gap-3 p-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold text-slate-900">
                          {listing.title}
                        </h3>
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                          {SOURCE_LABELS[listing.sourceSite] ??
                            listing.sourceSite}
                        </span>
                      </div>
                      {listing.rent != null && (
                        <p className="mt-1 text-sm font-medium text-indigo-600">
                          ${listing.rent.toLocaleString()}/mo
                        </p>
                      )}
                      {(() => {
                        const label = commuteLabelFromDistance(
                          listing.distanceMiles,
                          listing.commuteMinutes,
                          profile.commuteMode,
                        )
                        return label ? (
                          <p className="mt-1 text-xs font-medium text-emerald-700">
                            {label}
                            {listing.distanceMiles != null
                              ? ` (${listing.distanceMiles.toFixed(1)} mi)`
                              : ''}
                          </p>
                        ) : null
                      })()}
                      {listing.listingAddress && (
                        <p className="mt-1 text-xs text-slate-500">
                          {listing.listingAddress}
                        </p>
                      )}
                      <p className="mt-1 line-clamp-2 text-sm text-slate-600">
                        {listing.snippet}
                      </p>
                      <a
                        href={listing.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center gap-1 text-xs text-indigo-600 hover:underline"
                      >
                        <ExternalLink className="h-3 w-3" />
                        View on {listing.sourceSite}
                      </a>
                    </div>
                    {isAnalyzed && existing ? (
                      <div className="flex shrink-0 flex-col items-end gap-2">
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Already analyzed
                        </span>
                        {score != null && (
                          <ScoreBadge score={score} size="sm" />
                        )}
                        <Link
                          to={`/board/${existing.id}`}
                          className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
                        >
                          View on board
                        </Link>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleAdd(listing)}
                        disabled={
                          isAnalyzing ||
                          isAnalyzingAll ||
                          addingUrl === listing.url ||
                          isSubmitting
                        }
                        className="shrink-0"
                      >
                        {isAnalyzing || addingUrl === listing.url ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Analyzing...
                          </>
                        ) : (
                          <>
                            <Sparkles className="h-3.5 w-3.5" />
                            Analyze
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
