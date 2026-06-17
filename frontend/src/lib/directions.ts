export type DirectionsApp = 'google' | 'apple' | 'waze'

export interface DirectionsRoute {
  origin?: string
  destination: string
}

export function directionsAppsForRoute(route: DirectionsRoute): {
  id: DirectionsApp
  label: string
  description: string
}[] {
  const hasOrigin = Boolean(route.origin?.trim())
  const description = hasOrigin
    ? 'Turn-by-turn directions in maps'
    : 'From your location to this address'

  return [
    { id: 'google', label: 'Google Maps', description },
    { id: 'apple', label: 'Apple Maps', description },
    { id: 'waze', label: 'Waze', description: hasOrigin ? 'Navigate with Waze' : description },
  ]
}

/** Build a directions URL; omit origin to use the user's current location. */
export function directionsUrl(
  app: DirectionsApp,
  destination: string,
  origin?: string,
): string {
  const dest = encodeURIComponent(destination.trim())
  const orig = origin?.trim() ? encodeURIComponent(origin.trim()) : null

  switch (app) {
    case 'google':
      return orig
        ? `https://www.google.com/maps/dir/?api=1&origin=${orig}&destination=${dest}`
        : `https://www.google.com/maps/dir/?api=1&destination=${dest}`
    case 'apple':
      return orig
        ? `https://maps.apple.com/?saddr=${orig}&daddr=${dest}&dirflg=d`
        : `https://maps.apple.com/?daddr=${dest}&dirflg=d`
    case 'waze':
      return orig
        ? `https://www.waze.com/live-map/directions?navigate=yes&from=${orig}&to=${dest}`
        : `https://waze.com/ul?q=${dest}&navigate=yes`
  }
}

export function openDirections(
  app: DirectionsApp,
  destination: string,
  origin?: string,
): void {
  window.open(
    directionsUrl(app, destination, origin),
    '_blank',
    'noopener,noreferrer',
  )
}
