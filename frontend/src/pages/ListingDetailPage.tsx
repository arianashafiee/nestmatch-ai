import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ExternalLink, Loader2, RefreshCw, Star } from 'lucide-react'
import { AnalysisDashboard } from '@/components/apartments/AnalysisDashboard'
import { LandlordContactCard } from '@/components/apartments/LandlordContactCard'
import { LandlordMessageGenerator } from '@/components/apartments/LandlordMessageGenerator'
import { ListingMap } from '@/components/apartments/ListingMap'
import { ListingProgressChecklist } from '@/components/apartments/ListingProgressChecklist'
import { ParsingOverlay } from '@/components/apartments/ParsingOverlay'
import { PhotoGallery } from '@/components/apartments/PhotoGallery'
import { Button } from '@/components/ui/Button'
import { useApartments } from '@/context/ApartmentsContext'
import { refreshListingPhotos, fetchApartment } from '@/lib/api'
import { isSampleListing } from '@/lib/kanban'
import type { Apartment } from '@/types/apartment'
import { mapLocationForApartment } from '@/types/apartment'

export function ListingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { apartments, parsingIds, parseApartment, updateStatus, toggleFavorite, syncApartment } =
    useApartments()
  const [apartment, setApartment] = useState<Apartment | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshingPhotos, setIsRefreshingPhotos] = useState(false)

  const apartmentId = Number(id)
  const isParsing = parsingIds.includes(apartmentId)
  const sample = apartment ? isSampleListing(apartment.rawText) : false

  useEffect(() => {
    const fromContext = apartments.find((a) => a.id === apartmentId)
    if (fromContext?.analysis) {
      setApartment(fromContext)
      setIsLoading(false)
      return
    }

    fetchApartment(apartmentId)
      .then((data) => {
        setApartment(data)
        if (!data.analysis && data.status === 'pending') {
          parseApartment(data.id, data.rawText)
        }
      })
      .catch(() => setApartment(fromContext ?? null))
      .finally(() => setIsLoading(false))
  }, [apartmentId, apartments, parseApartment])

  useEffect(() => {
    const updated = apartments.find((a) => a.id === apartmentId)
    if (updated) setApartment(updated)
  }, [apartments, apartmentId])

  const handleRefreshPhotos = async () => {
    if (!apartment?.sourceUrl) return
    setIsRefreshingPhotos(true)
    try {
      const updated = await refreshListingPhotos(apartment.id)
      setApartment(updated)
      syncApartment(updated)
    } finally {
      setIsRefreshingPhotos(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  if (!apartment) {
    return (
      <div className="mx-auto max-w-lg text-center">
        <p className="text-slate-600">Listing not found.</p>
        <Link
          to="/board"
          className="mt-4 inline-flex h-10 items-center rounded-lg border border-slate-300 px-4 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Back to board
        </Link>
      </div>
    )
  }

  const analysis = apartment.analysis
  const mapLocation = mapLocationForApartment(apartment)

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link
        to="/board"
        className="inline-flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Hunting Board
      </Link>

      {sample && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          This is an older demo listing. Use <strong>Search all sites</strong> or
          paste a real apartments.com / Rent.com / Craigslist URL for live photos.
        </div>
      )}

      {apartment.sourceSite && (
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="rounded-full bg-slate-100 px-3 py-1 font-medium text-slate-700">
            via {apartment.sourceSite}
          </span>
          {apartment.status === 'interested' && (
            <button
              type="button"
              onClick={() =>
                toggleFavorite(apartment.id, !apartment.isFavorite)
              }
              className={
                apartment.isFavorite
                  ? 'inline-flex items-center gap-1 rounded-full bg-amber-50 px-3 py-1 font-medium text-amber-700'
                  : 'inline-flex items-center gap-1 rounded-full border border-slate-200 px-3 py-1 font-medium text-slate-600 hover:border-amber-200 hover:text-amber-700'
              }
            >
              <Star
                className={
                  apartment.isFavorite
                    ? 'h-3.5 w-3.5 fill-amber-400 text-amber-400'
                    : 'h-3.5 w-3.5'
                }
              />
              {apartment.isFavorite ? 'Favorited' : 'Add to favorites'}
            </button>
          )}
          {apartment.sourceUrl && (
            <a
              href={apartment.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-indigo-600 hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open original listing
            </a>
          )}
          {apartment.sourceUrl && (
            <Button
              size="sm"
              variant="ghost"
              onClick={handleRefreshPhotos}
              disabled={isRefreshingPhotos}
            >
              {isRefreshingPhotos ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Refresh photos
            </Button>
          )}
        </div>
      )}

      <PhotoGallery
        photos={apartment.photos ?? []}
        title={apartment.title ?? analysis?.title}
      />

      {analysis && apartment.status !== 'pending' && (
        <ListingProgressChecklist
          status={apartment.status}
          onStatusChange={(status) => updateStatus(apartment.id, status)}
        />
      )}

      {isParsing || (!analysis && apartment.status === 'pending') ? (
        <ParsingOverlay />
      ) : (
        <>
          {analysis && (
            <>
              <LandlordContactCard
                contact={apartment.landlordContact}
                sourceUrl={apartment.sourceUrl}
              />
              <ListingMap
                location={mapLocation}
                fallbackLabel={analysis.location}
                commuteMinutes={analysis.estimated_commute_minutes}
              />
            </>
          )}
          <AnalysisDashboard apartment={apartment} showRawText />
          {analysis && (
            <LandlordMessageGenerator
              analysis={analysis}
              landlordContact={apartment.landlordContact}
            />
          )}
        </>
      )}
    </div>
  )
}
