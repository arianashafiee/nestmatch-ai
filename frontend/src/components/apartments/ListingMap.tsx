import { useEffect, useRef, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { Loader2, MapPin, Navigation } from 'lucide-react'
import { fetchAppConfig } from '@/lib/api'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { MapPlaceholder } from '@/components/apartments/MapPlaceholder'

interface ListingMapProps {
  /** Street address or neighborhood to pin for the listing. */
  location: string
  /** Shown when location is missing or only campus is known. */
  fallbackLabel?: string
  commuteMinutes?: number | null
}

async function geocodeLocation(
  query: string,
  token: string,
  proximity?: [number, number],
): Promise<[number, number] | null> {
  const params = new URLSearchParams({
    access_token: token,
    limit: '1',
    country: 'us',
  })
  if (proximity) {
    params.set('proximity', `${proximity[0]},${proximity[1]}`)
  }
  const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?${params}`
  const response = await fetch(url)
  if (!response.ok) return null
  const data = (await response.json()) as {
    features?: { center: [number, number]; place_type?: string[] }[]
  }
  const feature = data.features?.[0]
  if (!feature?.center) return null
  return feature.center
}

function sameCoords(
  a: [number, number],
  b: [number, number],
  threshold = 0.0003,
): boolean {
  return (
    Math.abs(a[0] - b[0]) < threshold && Math.abs(a[1] - b[1]) < threshold
  )
}

export function ListingMap({
  location,
  fallbackLabel,
  commuteMinutes,
}: ListingMapProps) {
  const { profile } = useStudentProfile()
  const mapContainer = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [styleUrl, setStyleUrl] = useState('mapbox://styles/mapbox/streets-v12')
  const [loading, setLoading] = useState(true)
  const [mapError, setMapError] = useState<string | null>(null)

  const campus =
    profile.campusLocation || profile.university || 'Campus'

  useEffect(() => {
    fetchAppConfig()
      .then((config) => {
        setToken(config.mapboxToken)
        setStyleUrl(config.mapboxStyleUrl)
      })
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!token || !mapContainer.current) return

    let cancelled = false

    async function initMap() {
      setMapError(null)

      const campusCoords = await geocodeLocation(campus, token!)
      if (cancelled || !mapContainer.current) return

      let listingCoords: [number, number] | null = null
      if (location) {
        listingCoords = await geocodeLocation(
          location,
          token!,
          campusCoords ?? undefined,
        )
      }

      if (cancelled || !mapContainer.current) return

      if (
        listingCoords &&
        campusCoords &&
        sameCoords(listingCoords, campusCoords)
      ) {
        listingCoords = null
      }

      if (!listingCoords && !campusCoords) {
        setMapError('Could not find this address on the map.')
        return
      }

      const center = listingCoords ?? campusCoords!
      mapboxgl.accessToken = token!
      const map = new mapboxgl.Map({
        container: mapContainer.current,
        style: styleUrl,
        center,
        zoom: listingCoords ? 15 : 13,
      })
      mapRef.current = map

      if (listingCoords) {
        new mapboxgl.Marker({ color: '#4f46e5' })
          .setLngLat(listingCoords)
          .setPopup(new mapboxgl.Popup().setText(location))
          .addTo(map)
      }

      if (campusCoords) {
        new mapboxgl.Marker({ color: '#0f172a' })
          .setLngLat(campusCoords)
          .setPopup(new mapboxgl.Popup().setText(`${campus} (campus)`))
          .addTo(map)
      }

      if (listingCoords && campusCoords) {
        const bounds = new mapboxgl.LngLatBounds()
        bounds.extend(listingCoords)
        bounds.extend(campusCoords)
        map.fitBounds(bounds, { padding: 48, maxZoom: 15 })
      }

      if (!listingCoords) {
        setMapError(
          fallbackLabel
            ? `Exact listing address not available — showing campus only. (${fallbackLabel})`
            : 'Exact listing address not available — showing campus only.',
        )
      }

      map.addControl(new mapboxgl.NavigationControl(), 'top-right')
    }

    initMap().catch(() => {
      if (!cancelled) setMapError('Map failed to load.')
    })

    return () => {
      cancelled = true
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [token, styleUrl, location, campus, fallbackLabel])

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-slate-200 bg-slate-50">
        <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
      </div>
    )
  }

  if (!token) {
    return (
      <MapPlaceholder location={location || fallbackLabel || campus} commuteMinutes={commuteMinutes} />
    )
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="relative h-56">
        <div ref={mapContainer} className="h-full w-full" />
        {mapError && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-amber-50/95 px-4 py-2 text-center">
            <p className="text-xs text-amber-900">{mapError}</p>
          </div>
        )}
      </div>
      {location && !mapError && (
        <div className="flex items-center gap-2 border-t border-slate-100 px-4 py-2 text-xs text-slate-600">
          <MapPin className="h-3.5 w-3.5 shrink-0 text-indigo-600" />
          <span className="truncate">{location}</span>
        </div>
      )}
      {commuteMinutes != null && (
        <div className="flex items-center gap-2 border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
          <Navigation className="h-4 w-4 text-indigo-600" />
          Estimated {commuteMinutes} min {profile.commuteMode} to campus
        </div>
      )}
    </div>
  )
}
