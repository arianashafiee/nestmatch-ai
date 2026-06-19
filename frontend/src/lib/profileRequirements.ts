import type { SearchListingResult } from '@/types/apartment'
import type { StudentProfile } from '@/types/studentProfile'

const BEDROOM_COUNT_PATTERNS = [
  /(\d+(?:\.\d+)?)\s*(?:bedrooms?|beds?)\b/gi,
  /(\d+(?:\.\d+)?)\s*[-\s]?(?:br|bd)\b/gi,
  /(\d+(?:\.\d+)?)\s*(?:br|bd)\s*\//gi,
  /\b(\d+)\s*\/\s*(\d+(?:\.\d+)?)\s*(?:ba|bath|baths)\b/gi,
]

const BEDROOM_RANGE_PATTERNS = [
  /(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:bedrooms?|beds?|br|bd)\b/gi,
  /(\d+)\s*(?:bedrooms?|beds?|br|bd)\s*(?:-|–|to)\s*(\d+)\b/gi,
  /studio\s*(?:-|–|to)\s*(\d+)\s*(?:beds?|br|bd)\b/gi,
]

export function requiredBedrooms(profile: StudentProfile): number {
  if (
    profile.livingSituation === 'roommates' &&
    profile.roommateCount > 0
  ) {
    return profile.roommateCount + 1
  }
  return 1
}

export function bedroomRequirementLabel(profile: StudentProfile): string {
  const required = requiredBedrooms(profile)
  if (required === 1) return 'studio or 1-bedroom'
  return `${required}-bedroom`
}

function addCount(counts: Set<number>, value: number): void {
  if (value < 0 || !Number.isFinite(value)) return
  counts.add(Math.round(value))
}

export function parseBedroomCountsFromText(text: string): Set<number> {
  const counts = new Set<number>()
  if (!text) return counts

  if (/\bstudio\b/i.test(text)) counts.add(0)

  for (const pattern of BEDROOM_RANGE_PATTERNS) {
    pattern.lastIndex = 0
    let match = pattern.exec(text)
    while (match) {
      if (pattern.source.startsWith('studio')) {
        const end = Number.parseInt(match[1], 10)
        for (let bed = 0; bed <= end; bed += 1) counts.add(bed)
      } else {
        const start = Number.parseInt(match[1], 10)
        const end = Number.parseInt(match[2], 10)
        const low = Math.min(start, end)
        const high = Math.max(start, end)
        for (let bed = low; bed <= high; bed += 1) counts.add(bed)
      }
      match = pattern.exec(text)
    }
  }

  for (const pattern of BEDROOM_COUNT_PATTERNS) {
    pattern.lastIndex = 0
    let match = pattern.exec(text)
    while (match) {
      addCount(counts, Number.parseFloat(match[1]))
      match = pattern.exec(text)
    }
  }

  return counts
}

export function listingOfferedBedCounts(
  listing: SearchListingResult,
): Set<number> {
  const counts = parseBedroomCountsFromText(
    `${listing.title} ${listing.snippet}`.trim(),
  )
  if (listing.bedrooms != null) {
    addCount(counts, listing.bedrooms)
  }
  return counts
}

export function listingMatchesBedroomRequirement(
  listing: SearchListingResult,
  profile: StudentProfile,
): boolean {
  const required = requiredBedrooms(profile)
  const counts = listingOfferedBedCounts(listing)
  if (counts.size === 0) return false
  if (required === 1) return counts.has(0) || counts.has(1)
  return counts.has(required)
}

export function listingBedrooms(listing: SearchListingResult): number | null {
  if (listing.bedrooms != null) return listing.bedrooms
  const counts = parseBedroomCountsFromText(`${listing.title} ${listing.snippet}`)
  if (counts.size === 0) return null
  return Math.max(...counts)
}

export function filterListingsByBedroomRequirement(
  listings: SearchListingResult[],
  profile: StudentProfile,
): SearchListingResult[] {
  return listings.filter((listing) =>
    listingMatchesBedroomRequirement(listing, profile),
  )
}
