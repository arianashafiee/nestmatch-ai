import type { Apartment, SearchListingResult } from '@/types/apartment'
import { listingTitleFromApartment } from '@/types/apartment'

export function normalizeListingUrl(url: string): string {
  try {
    const parsed = new URL(url.trim())
    const path = parsed.pathname.replace(/\/+$/, '') || '/'
    return `${parsed.protocol}//${parsed.host.toLowerCase()}${path}`
  } catch {
    return url.trim().toLowerCase()
  }
}

export function findApartmentByListingUrl(
  apartments: Apartment[],
  listingUrl: string,
): Apartment | undefined {
  const normalized = normalizeListingUrl(listingUrl)
  return apartments.find(
    (apartment) =>
      apartment.sourceUrl &&
      normalizeListingUrl(apartment.sourceUrl) === normalized,
  )
}

export function isApartmentAnalyzed(apartment: Apartment): boolean {
  return apartment.analysis != null
}

export function getListingCompatibilityScore(
  apartments: Apartment[],
  listingUrl: string,
): number | null {
  const apartment = findApartmentByListingUrl(apartments, listingUrl)
  if (!apartment) return null
  return (
    apartment.compatibilityScore ??
    apartment.analysis?.compatibility_score ??
    null
  )
}

export function isListingEligibleForAnalysis(
  apartments: Apartment[],
  listingUrl: string,
  parsingIds: number[],
): boolean {
  const existing = findApartmentByListingUrl(apartments, listingUrl)
  if (!existing) return true
  if (isApartmentAnalyzed(existing)) return false
  if (parsingIds.includes(existing.id)) return false
  return true
}

export function sortSearchResultsByScore(
  results: SearchListingResult[],
  apartments: Apartment[],
): SearchListingResult[] {
  return [...results].sort((a, b) => {
    const scoreA = getListingCompatibilityScore(apartments, a.url) ?? -1
    const scoreB = getListingCompatibilityScore(apartments, b.url) ?? -1
    if (scoreA !== scoreB) return scoreB - scoreA
    return 0
  })
}

export function confirmDeleteListing(apartment: Apartment): boolean {
  const title = listingTitleFromApartment(apartment)
  return window.confirm(
    `Remove "${title}" from your shortlist? This cannot be undone.`,
  )
}
