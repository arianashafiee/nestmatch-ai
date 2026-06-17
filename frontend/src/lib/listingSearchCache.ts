import type { SearchListingResult } from '@/types/apartment'
import type { StudentProfile } from '@/types/studentProfile'

export interface ListingSearchState {
  results: SearchListingResult[]
  sourcesSearched: string[]
  searchErrors: Record<string, string>
  searchArea: string
  searchMeta: {
    campusGeocoded: boolean
    maxCommuteMinutes: number
    commuteMode: string
    aiRanked: boolean
  } | null
  profileFingerprint: string
  searchedAt: number
}

export function listingSearchStorageKey(userId: number): string {
  return `nestmatch-listing-search-${userId}`
}

/** Profile fields that affect multi-site search, commute filter, and AI ranking. */
export function searchProfileFingerprint(profile: StudentProfile): string {
  return JSON.stringify({
    university: profile.university.trim(),
    campusLocation: profile.campusLocation.trim(),
    maxRent: profile.maxRent,
    maxCommuteMinutes: profile.maxCommuteMinutes,
    commuteMode: profile.commuteMode,
    livingSituation: profile.livingSituation,
    roommateCount: profile.roommateCount,
    mustHaves: [...profile.mustHaves].sort(),
    dealbreakers: [...profile.dealbreakers].sort(),
    preferredLeaseLength: profile.preferredLeaseLength.trim(),
  })
}

export function loadListingSearchCache(
  userId: number,
): ListingSearchState | null {
  try {
    const raw = localStorage.getItem(listingSearchStorageKey(userId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as ListingSearchState
    if (!parsed || !Array.isArray(parsed.results)) return null
    return parsed
  } catch {
    return null
  }
}

export function persistListingSearchCache(
  userId: number,
  state: ListingSearchState,
): void {
  localStorage.setItem(listingSearchStorageKey(userId), JSON.stringify(state))
}

export function clearListingSearchCache(userId: number): void {
  localStorage.removeItem(listingSearchStorageKey(userId))
}
