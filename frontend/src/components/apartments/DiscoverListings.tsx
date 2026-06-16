import { useState } from 'react'
import { ExternalLink, Loader2, Search, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { searchListings } from '@/lib/api'
import { useApartments } from '@/context/ApartmentsContext'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { useToast } from '@/context/ToastContext'
import { cn } from '@/lib/utils'
import type { SearchListingResult } from '@/types/apartment'
import { photoProxyUrl } from '@/types/apartment'

const SOURCE_LABELS: Record<string, string> = {
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
  const { addApartment, isSubmitting } = useApartments()
  const { showToast } = useToast()

  const [isSearching, setIsSearching] = useState(false)
  const [results, setResults] = useState<SearchListingResult[]>([])
  const [sourcesSearched, setSourcesSearched] = useState<string[]>([])
  const [searchErrors, setSearchErrors] = useState<Record<string, string>>({})
  const [searchArea, setSearchArea] = useState('')
  const [searchMeta, setSearchMeta] = useState<{
    campusGeocoded: boolean
    maxCommuteMinutes: number
    commuteMode: string
    aiRanked: boolean
  } | null>(null)
  const [addingUrl, setAddingUrl] = useState<string | null>(null)

  const area = profile.campusLocation || profile.university

  const handleSearch = async () => {
    if (!isProfileComplete) return
    setIsSearching(true)
    setResults([])
    try {
      const data = await searchListings(1)
      setResults(data.results)
      setSourcesSearched(data.sourcesSearched)
      setSearchErrors(data.errors)
      setSearchArea(data.searchArea)
      setSearchMeta({
        campusGeocoded: data.campusGeocoded,
        maxCommuteMinutes: data.maxCommuteMinutes,
        commuteMode: data.commuteMode,
        aiRanked: data.aiRanked,
      })
      if (data.results.length === 0) {
        showToast(
          'No listings found — sites may block automated search. Try pasting a direct link.',
          'info',
        )
      } else {
        showToast(
          data.aiRanked
            ? `Found ${data.results.length} listings — ranked by AI for your profile`
            : `Found ${data.results.length} listings across ${data.sourcesSearched.length} sites`,
          'success',
        )
      }
    } catch (err) {
      showToast(
        err instanceof Error ? err.message : 'Search failed',
        'error',
      )
    } finally {
      setIsSearching(false)
    }
  }

  const handleAdd = async (listing: SearchListingResult) => {
    setAddingUrl(listing.url)
    await addApartment(listing.rawText, {
      sourceUrl: listing.url,
      photos: listing.photos,
      sourceSite: listing.sourceSite,
    })
    setAddingUrl(null)
    onAdded?.()
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
        <p className="font-medium">Automatic search across rental sites</p>
        <p className="mt-1 text-indigo-800">
          NestMatch searches <strong>Apartments.com</strong>, <strong>Rent.com</strong>,{' '}
          <strong>Zillow</strong>, <strong>Craigslist</strong>, and <strong>Realtor.com</strong>{' '}
          near your campus address, filtered by your max{' '}
          {profile.commuteMode} commute ({profile.maxCommuteMinutes} min) and budget (
          ${profile.maxRent}/mo). With <strong>OpenAI</strong> configured, results are also
          AI-ranked and summarized for your profile.
        </p>
      </div>

      {!isProfileComplete ? (
        <p className="text-sm text-amber-700">
          Complete your profile with campus location and budget to search.
        </p>
      ) : (
        <Button onClick={handleSearch} disabled={isSearching || isSubmitting}>
          {isSearching ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Searching near {area}...
            </>
          ) : (
            <>
              <Search className="h-4 w-4" />
              Search all sites near campus
            </>
          )}
        </Button>
      )}

      {searchMeta?.aiRanked && (
        <p className="text-xs font-medium text-indigo-700">
          Results ranked by OpenAI based on your budget, commute, and preferences.
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
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {results.length} real listings found
          </p>
          {results.map((listing) => (
            <div
              key={listing.url}
              className="overflow-hidden rounded-xl border border-slate-200 bg-white"
            >
              <div className="flex flex-col sm:flex-row">
                {listing.photos[0] ? (
                  <img
                    src={photoProxyUrl(listing.photos[0])}
                    alt=""
                    className="h-36 w-full object-cover sm:h-auto sm:w-40 shrink-0"
                    onError={(e) => {
                      e.currentTarget.src = listing.photos[0]
                    }}
                  />
                ) : (
                  <div className="flex h-28 w-full shrink-0 items-center justify-center bg-slate-100 sm:w-40">
                    <span className="text-xs text-slate-400">Photo on add</span>
                  </div>
                )}
                <div className="flex flex-1 items-start justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-slate-900">
                        {listing.title}
                      </h3>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                        {SOURCE_LABELS[listing.sourceSite] ?? listing.sourceSite}
                      </span>
                    </div>
                    {listing.rent != null && (
                      <p className="mt-1 text-sm font-medium text-indigo-600">
                        ${listing.rent.toLocaleString()}/mo
                      </p>
                    )}
                    {listing.commuteMinutes != null && (
                      <p className="mt-1 text-xs font-medium text-emerald-700">
                        ~{listing.commuteMinutes} min {profile.commuteMode} to campus
                        {listing.distanceMiles != null
                          ? ` (${listing.distanceMiles.toFixed(1)} mi)`
                          : ''}
                      </p>
                    )}
                    {listing.listingAddress && (
                      <p className="mt-1 text-xs text-slate-500">{listing.listingAddress}</p>
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
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleAdd(listing)}
                    disabled={addingUrl === listing.url}
                    className="shrink-0"
                  >
                    {addingUrl === listing.url ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <Sparkles className="h-3.5 w-3.5" />
                        Analyze
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
