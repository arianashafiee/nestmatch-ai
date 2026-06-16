export type ApartmentStatus =
  | 'pending'
  | 'interested'
  | 'contacted'
  | 'tour_scheduled'
  | 'applied'
  | 'archived'

export interface ScoreBreakdown {
  affordability: number
  commute: number
  amenities: number
  safety_comfort: number
  student_fit: number
}

export interface ListingAnalysis {
  title: string
  rent_monthly: number | null
  location: string
  bedrooms: number | null
  bathrooms: number | null
  amenities: string[]
  hidden_fees: string[]
  lease_length: string | null
  red_flags: string[]
  missing_info: string[]
  estimated_commute_minutes: number | null
  compatibility_score: number
  score_breakdown: ScoreBreakdown
  pros: string[]
  cons: string[]
  follow_up_questions: string[]
}

export interface LandlordContact {
  name: string | null
  phone: string | null
  email: string | null
  contactUrl: string | null
}

export interface Apartment {
  id: number
  profileId: number
  rawText: string
  sourceUrl: string | null
  status: ApartmentStatus
  title: string | null
  compatibilityScore: number | null
  analysis: ListingAnalysis | null
  photos: string[]
  sourceSite: string | null
  landlordContact: LandlordContact | null
  parsedAt: string | null
  createdAt: string
}

export interface SearchListingResult {
  title: string
  url: string
  sourceSite: string
  rent: number | null
  bedrooms: number | null
  bathrooms: number | null
  snippet: string
  photos: string[]
  location: string
  rawText: string
}

export interface SearchListingsResponse {
  results: SearchListingResult[]
  sourcesSearched: string[]
  errors: Record<string, string>
  location: string
  maxRent: number
}

function analysisFromApi(data: unknown): ListingAnalysis | null {
  if (!data || typeof data !== 'object') return null
  const a = data as Record<string, unknown>
  const breakdown = a.score_breakdown as Record<string, number>
  return {
    title: String(a.title ?? ''),
    rent_monthly: (a.rent_monthly as number | null) ?? null,
    location: String(a.location ?? ''),
    bedrooms: (a.bedrooms as number | null) ?? null,
    bathrooms: (a.bathrooms as number | null) ?? null,
    amenities: (a.amenities as string[]) ?? [],
    hidden_fees: (a.hidden_fees as string[]) ?? [],
    lease_length: (a.lease_length as string | null) ?? null,
    red_flags: (a.red_flags as string[]) ?? [],
    missing_info: (a.missing_info as string[]) ?? [],
    estimated_commute_minutes:
      (a.estimated_commute_minutes as number | null) ?? null,
    compatibility_score: Number(a.compatibility_score ?? 0),
    score_breakdown: {
      affordability: breakdown?.affordability ?? 0,
      commute: breakdown?.commute ?? 0,
      amenities: breakdown?.amenities ?? 0,
      safety_comfort: breakdown?.safety_comfort ?? 0,
      student_fit: breakdown?.student_fit ?? 0,
    },
    pros: (a.pros as string[]) ?? [],
    cons: (a.cons as string[]) ?? [],
    follow_up_questions: (a.follow_up_questions as string[]) ?? [],
  }
}

function landlordContactFromApi(data: unknown): LandlordContact | null {
  if (!data || typeof data !== 'object') return null
  const c = data as Record<string, unknown>
  if (!c.name && !c.phone && !c.email && !c.contact_url) return null
  return {
    name: (c.name as string | null) ?? null,
    phone: (c.phone as string | null) ?? null,
    email: (c.email as string | null) ?? null,
    contactUrl: (c.contact_url as string | null) ?? null,
  }
}

export function apartmentFromApi(data: Record<string, unknown>): Apartment {
  return normalizeApartment({
    id: data.id as number,
    profileId: data.profile_id as number,
    rawText: data.raw_text as string,
    sourceUrl: (data.source_url as string | null) ?? null,
    status: data.status as ApartmentStatus,
    title: (data.title as string | null) ?? null,
    compatibilityScore: (data.compatibility_score as number | null) ?? null,
    analysis: analysisFromApi(data.analysis),
    photos: (data.photos as string[]) ?? [],
    sourceSite: (data.source_site as string | null) ?? null,
    landlordContact: landlordContactFromApi(data.landlord_contact),
    parsedAt: (data.parsed_at as string | null) ?? null,
    createdAt: data.created_at as string,
  })
}

/** Ensures apartments from localStorage or older API responses have all fields. */
export function normalizeApartment(apt: Partial<Apartment> & { id: number }): Apartment {
  return {
    id: apt.id,
    profileId: apt.profileId ?? 1,
    rawText: apt.rawText ?? '',
    sourceUrl: apt.sourceUrl ?? null,
    status: apt.status ?? 'pending',
    title: apt.title ?? null,
    compatibilityScore: apt.compatibilityScore ?? null,
    analysis: apt.analysis ? analysisFromApi(apt.analysis) : null,
    photos: Array.isArray(apt.photos) ? apt.photos : [],
    sourceSite: apt.sourceSite ?? null,
    landlordContact: apt.landlordContact ?? null,
    parsedAt: apt.parsedAt ?? null,
    createdAt: apt.createdAt ?? new Date().toISOString(),
  }
}

export function searchResultFromApi(
  data: Record<string, unknown>,
): SearchListingResult {
  return {
    title: data.title as string,
    url: data.url as string,
    sourceSite: data.source_site as string,
    rent: (data.rent as number | null) ?? null,
    bedrooms: (data.bedrooms as number | null) ?? null,
    bathrooms: (data.bathrooms as number | null) ?? null,
    snippet: (data.snippet as string) ?? '',
    photos: (data.photos as string[]) ?? [],
    location: (data.location as string) ?? '',
    rawText: (data.raw_text as string) ?? '',
  }
}

export function photoProxyUrl(imageUrl: string): string {
  return `/api/photos/proxy?url=${encodeURIComponent(imageUrl)}`
}

export const SCORE_CATEGORIES: {
  key: keyof ScoreBreakdown
  label: string
}[] = [
  { key: 'affordability', label: 'Affordability' },
  { key: 'commute', label: 'Commute' },
  { key: 'amenities', label: 'Amenities' },
  { key: 'safety_comfort', label: 'Safety & Comfort' },
  { key: 'student_fit', label: 'Student Fit' },
]

export function scoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-600'
  if (score >= 60) return 'text-indigo-600'
  if (score >= 40) return 'text-amber-600'
  return 'text-red-600'
}

export function scoreBg(score: number): string {
  if (score >= 80) return 'bg-emerald-50 border-emerald-200'
  if (score >= 60) return 'bg-indigo-50 border-indigo-200'
  if (score >= 40) return 'bg-amber-50 border-amber-200'
  return 'bg-red-50 border-red-200'
}
