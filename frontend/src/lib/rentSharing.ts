import type { StudentProfile } from '@/types/studentProfile'
import { requiredBedrooms } from '@/lib/profileRequirements'

const PER_PERSON_RENT_RE =
  /\b(?:per\s+(?:person|tenant|occupant|roommate)|\/\s*person\b|each\s+person)\b/i

const RENT_BED_TIER_STUDIO_RE =
  /\$\s*([\d,]+)\s*-\s*\$\s*([\d,]+)(?:\s*\/?\s*(?:bedroom?|bd))?\s*(?:·|\||-)?\s*studio\s*-\s*(\d+)\s*(?:beds?|br|bd)\b/gi

const RENT_BED_TIER_NUMERIC_RE =
  /\$\s*([\d,]+)\s*-\s*\$\s*([\d,]+)(?:\s*\/?\s*(?:bedroom?|bd))?\s*(?:·|\||-)?\s*(\d+)\s*-\s*(\d+)\s*(?:beds?|br|bd)\b/gi

export function occupantCount(profile: StudentProfile): number {
  if (profile.livingSituation === 'roommates' && profile.roommateCount > 0) {
    return profile.roommateCount + 1
  }
  return 1
}

export function listingRentIsPerPerson(text: string): boolean {
  return PER_PERSON_RENT_RE.test(text)
}

function parseMoney(value: string): number {
  return Number.parseFloat(value.replace(/,/g, ''))
}

function rentForBedInTier(
  requiredBeds: number,
  bedMin: number,
  bedMax: number,
  rentMin: number,
  rentMax: number,
): number {
  if (bedMax <= bedMin) {
    return requiredBeds >= bedMax ? rentMax : rentMin
  }
  const ratio = Math.max(0, Math.min(1, (requiredBeds - bedMin) / (bedMax - bedMin)))
  return rentMin + (rentMax - rentMin) * ratio
}

export function rentForBedroomCount(
  text: string,
  requiredBeds: number,
  fallbackRent?: number | null,
): number | null {
  if (!text.trim()) {
    return fallbackRent ?? null
  }

  let best: number | null = null
  const tiers: Array<{
    pattern: RegExp
    studioTier: boolean
  }> = [
    { pattern: RENT_BED_TIER_STUDIO_RE, studioTier: true },
    { pattern: RENT_BED_TIER_NUMERIC_RE, studioTier: false },
  ]

  for (const { pattern, studioTier } of tiers) {
    pattern.lastIndex = 0
    let match = pattern.exec(text)
    while (match) {
      const rentMin = parseMoney(match[1])
      const rentMax = parseMoney(match[2])
      const bedMin = studioTier ? 0 : Number.parseInt(match[3], 10)
      const bedMax = studioTier
        ? Number.parseInt(match[3], 10)
        : Number.parseInt(match[4], 10)

      if (requiredBeds === 1 && bedMin <= 1 && bedMax >= 1) {
        const tierRent = rentForBedInTier(1, bedMin, bedMax, rentMin, rentMax)
        best = best == null ? tierRent : Math.min(best, tierRent)
      } else if (bedMin <= requiredBeds && requiredBeds <= bedMax) {
        const tierRent = rentForBedInTier(
          requiredBeds,
          bedMin,
          bedMax,
          rentMin,
          rentMax,
        )
        best = best == null ? tierRent : Math.min(best, tierRent)
      }

      match = pattern.exec(text)
    }
  }

  return best ?? fallbackRent ?? null
}

export function unitRentForProfile(
  rent: number | null | undefined,
  profile: StudentProfile,
  text = '',
): number | null {
  const required = requiredBedrooms(profile)
  return rentForBedroomCount(text, required, rent ?? null)
}

export function rentPerPersonForProfile(
  rent: number,
  profile: StudentProfile,
  text = '',
): number {
  const unitRent = unitRentForProfile(rent, profile, text) ?? rent
  if (listingRentIsPerPerson(text)) return unitRent
  const occupants = occupantCount(profile)
  if (occupants <= 1) return unitRent
  return unitRent / occupants
}

export function listingWithinRentBudget(
  rent: number | null | undefined,
  profile: StudentProfile,
  text = '',
): boolean {
  if (rent == null) return true
  return rentPerPersonForProfile(rent, profile, text) <= profile.maxRent
}

export interface RentDisplayInfo {
  total: number
  perPerson: number
  occupants: number
  isPerPersonListing: boolean
}

export function rentDisplayInfo(
  rent: number,
  profile: StudentProfile,
  text = '',
): RentDisplayInfo {
  const occupants = occupantCount(profile)
  const isPerPersonListing = listingRentIsPerPerson(text)
  const total = unitRentForProfile(rent, profile, text) ?? rent
  if (isPerPersonListing) {
    return {
      total: total * occupants,
      perPerson: total,
      occupants,
      isPerPersonListing: true,
    }
  }
  return {
    total,
    perPerson: occupants > 1 ? total / occupants : total,
    occupants,
    isPerPersonListing: false,
  }
}

export function formatRentForProfile(
  rent: number,
  profile: StudentProfile,
  text = '',
): string {
  const info = rentDisplayInfo(rent, profile, text)
  if (info.occupants <= 1) {
    return `$${Math.round(info.total).toLocaleString()}/mo`
  }
  if (info.isPerPersonListing) {
    return `$${Math.round(info.perPerson).toLocaleString()}/mo per person`
  }
  return `$${Math.round(info.total).toLocaleString()}/mo total · $${Math.round(info.perPerson).toLocaleString()}/person`
}

export function rentBudgetLabel(profile: StudentProfile): string {
  if (occupantCount(profile) > 1) {
    return `$${profile.maxRent.toLocaleString()}/mo per person`
  }
  return `$${profile.maxRent.toLocaleString()}/mo`
}
