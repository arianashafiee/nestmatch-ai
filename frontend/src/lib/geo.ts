/** Shared geocoding and Mapbox route helpers for commute estimates. */

import { fetchAppConfig } from '@/lib/api'
import type { CommuteMode } from '@/types/studentProfile'

/** Fallback speeds when Mapbox is unavailable (match backend geo.py). */
export const COMMUTE_SPEED_MPH: Record<CommuteMode, number> = {
  walking: 3,
  biking: 10,
  transit: 18,
  driving: 25,
}

const MAPBOX_DIRECTIONS_PROFILE: Record<CommuteMode, string> = {
  walking: 'walking',
  driving: 'driving',
  biking: 'cycling',
  transit: 'driving',
}

const METERS_TO_MILES = 0.000621371

const geocodeCache = new Map<string, Promise<[number, number] | null>>()
const routeCache = new Map<
  string,
  Promise<{ distanceMiles: number; minutes: number } | null>
>()

export function haversineMiles(
  a: [number, number],
  b: [number, number],
): number {
  const [lon1, lat1] = a
  const [lon2, lat2] = b
  const radius = 3958.8
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLon = ((lon2 - lon1) * Math.PI) / 180
  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2
  return radius * 2 * Math.asin(Math.sqrt(x))
}

export async function geocodeAddress(
  query: string,
  token: string,
  proximity?: [number, number],
): Promise<[number, number] | null> {
  const normalized = query.trim().toLowerCase()
  if (!normalized) return null

  const cacheKey = `${normalized}|${proximity?.join(',') ?? ''}`
  const cached = geocodeCache.get(cacheKey)
  if (cached) return cached

  const promise = (async () => {
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
      features?: { center: [number, number] }[]
    }
    return data.features?.[0]?.center ?? null
  })()

  geocodeCache.set(cacheKey, promise)
  return promise
}

export function estimateCommuteMinutes(
  distanceMiles: number,
  mode: CommuteMode,
): number {
  if (distanceMiles <= 0) return 0
  const speed = COMMUTE_SPEED_MPH[mode] ?? COMMUTE_SPEED_MPH.walking
  return Math.max(1, Math.round((distanceMiles / speed) * 60))
}

function commuteFromRoute(
  distanceMeters: number,
  durationSeconds: number,
  mode: CommuteMode,
): { distanceMiles: number; minutes: number } {
  const distanceMiles = Math.round(distanceMeters * METERS_TO_MILES * 100) / 100
  const minutes =
    mode === 'transit'
      ? estimateCommuteMinutes(distanceMiles, 'transit')
      : Math.max(1, Math.round(durationSeconds / 60))
  return { distanceMiles, minutes }
}

/** Mapbox Directions route distance (mi) and travel time (min) between two points. */
export async function fetchMapboxRouteCommute(
  origin: [number, number],
  destination: [number, number],
  token: string,
  mode: CommuteMode,
): Promise<{ distanceMiles: number; minutes: number } | null> {
  const profile = MAPBOX_DIRECTIONS_PROFILE[mode]
  const cacheKey = `${profile}|${origin.join(',')}|${destination.join(',')}`
  const cached = routeCache.get(cacheKey)
  if (cached) return cached

  const promise = (async () => {
    const coordinates = `${origin[0]},${origin[1]};${destination[0]},${destination[1]}`
    const params = new URLSearchParams({
      access_token: token,
      overview: 'false',
      alternatives: 'false',
    })
    const url = `https://api.mapbox.com/directions/v5/mapbox/${profile}/${coordinates}?${params}`
    const response = await fetch(url)
    if (!response.ok) return null

    const data = (await response.json()) as {
      routes?: { distance: number; duration: number }[]
    }
    const route = data.routes?.[0]
    if (!route) return null

    return commuteFromRoute(route.distance, route.duration, mode)
  })()

  routeCache.set(cacheKey, promise)
  return promise
}

/** Geocode campus + listing and return Mapbox route miles and minutes. */
export async function fetchMapboxCommuteBetweenAddresses(
  campusAddress: string,
  listingAddress: string,
  mode: CommuteMode,
): Promise<{ distanceMiles: number; minutes: number } | null> {
  const config = await fetchAppConfig()
  if (!config.mapboxToken) return null

  const campusCoords = await geocodeAddress(campusAddress, config.mapboxToken)
  if (!campusCoords) return null

  const listingCoords = await geocodeAddress(
    listingAddress,
    config.mapboxToken,
    campusCoords,
  )
  if (!listingCoords) return null

  const routed = await fetchMapboxRouteCommute(
    campusCoords,
    listingCoords,
    config.mapboxToken,
    mode,
  )
  if (routed) return routed

  const distanceMiles =
    Math.round(haversineMiles(campusCoords, listingCoords) * 100) / 100
  return {
    distanceMiles,
    minutes: estimateCommuteMinutes(distanceMiles, mode),
  }
}

/** @deprecated use fetchMapboxCommuteBetweenAddresses */
export async function fetchDistanceMilesBetweenAddresses(
  campusAddress: string,
  listingAddress: string,
): Promise<number | null> {
  const estimate = await fetchMapboxCommuteBetweenAddresses(
    campusAddress,
    listingAddress,
    'walking',
  )
  return estimate?.distanceMiles ?? null
}

export async function estimateCommuteClientSide(
  campusAddress: string,
  listingAddress: string,
  mode: CommuteMode,
): Promise<{ minutes: number; distanceMiles: number } | null> {
  return fetchMapboxCommuteBetweenAddresses(campusAddress, listingAddress, mode)
}
