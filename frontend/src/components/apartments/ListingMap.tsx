import { useEffect, useRef, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { Loader2, MapPin, Navigation } from 'lucide-react'
import { fetchAppConfig } from '@/lib/api'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { MapPlaceholder } from '@/components/apartments/MapPlaceholder'

interface ListingMapProps {
  location: string
  commuteMinutes?: number | null
}

async function geocodeLocation(
  query: string,
  token: string,
): Promise<[number, number] | null> {
  const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?access_token=${token}&limit=1`
  const response = await fetch(url)
  if (!response.ok) return null
  const data = (await response.json()) as {
    features?: { center: [number, number] }[]
  }
  return data.features?.[0]?.center ?? null
}

export function ListingMap({ location, commuteMinutes }: ListingMapProps) {
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
    if (!token || !mapContainer.current || !location) return

    let cancelled = false

    async function initMap() {
      setMapError(null)
      const coords = await geocodeLocation(location, token!)
      if (cancelled || !mapContainer.current) return

      if (!coords) {
        setMapError('Could not find this address on the map.')
        return
      }

      mapboxgl.accessToken = token!
      const map = new mapboxgl.Map({
        container: mapContainer.current,
        style: styleUrl,
        center: coords,
        zoom: 14,
      })
      mapRef.current = map

      new mapboxgl.Marker({ color: '#4f46e5' })
        .setLngLat(coords)
        .setPopup(new mapboxgl.Popup().setText(location))
        .addTo(map)

      const campusCoords = await geocodeLocation(campus, token!)
      if (!cancelled && campusCoords) {
        new mapboxgl.Marker({ color: '#0f172a' })
          .setLngLat(campusCoords)
          .setPopup(new mapboxgl.Popup().setText(`${campus} (campus)`))
          .addTo(map)

        const bounds = new mapboxgl.LngLatBounds()
        bounds.extend(coords)
        bounds.extend(campusCoords)
        map.fitBounds(bounds, { padding: 48, maxZoom: 13 })
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
  }, [token, styleUrl, location, campus])

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-slate-200 bg-slate-50">
        <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
      </div>
    )
  }

  if (!token) {
    return (
      <MapPlaceholder location={location} commuteMinutes={commuteMinutes} />
    )
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="relative h-56">
        <div ref={mapContainer} className="h-full w-full" />
        {mapError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50/95 px-4 text-center">
            <MapPin className="h-8 w-8 text-indigo-600" />
            <p className="mt-2 text-sm font-medium text-slate-700">{location}</p>
            <p className="mt-1 text-xs text-slate-500">{mapError}</p>
          </div>
        )}
      </div>
      {commuteMinutes != null && (
        <div className="flex items-center gap-2 border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
          <Navigation className="h-4 w-4 text-indigo-600" />
          Estimated {commuteMinutes} min {profile.commuteMode} to campus
        </div>
      )}
    </div>
  )
}
