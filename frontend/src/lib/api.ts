import type { Apartment, SearchListingsResponse } from '@/types/apartment'
import { apartmentFromApi, searchResultFromApi } from '@/types/apartment'
import {
  profileFromApi,
  profileToApi,
  type StudentProfile,
} from '@/types/studentProfile'

const API_BASE = '/api'

function getAuthToken(): string | null {
  return localStorage.getItem('nestmatch-auth-token')
}

function parseErrorDetail(body: unknown, status: number): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === 'object' && item && 'msg' in item
            ? String((item as { msg: string }).msg)
            : String(item),
        )
        .join(', ')
    }
  }
  return `Request failed (${status})`
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const token = getAuthToken()
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(parseErrorDetail(error, response.status))
  }

  return response.json() as Promise<T>
}

export interface AuthUser {
  id: number
  email: string
}

export async function registerUser(
  email: string,
  password: string,
): Promise<{ accessToken: string; user: AuthUser }> {
  const data = await request<{ access_token: string; user: AuthUser }>(
    '/auth/register',
    {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    },
  )
  return { accessToken: data.access_token, user: data.user }
}

export async function loginUser(
  email: string,
  password: string,
): Promise<{ accessToken: string; user: AuthUser }> {
  const data = await request<{ access_token: string; user: AuthUser }>(
    '/auth/login',
    {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    },
  )
  return { accessToken: data.access_token, user: data.user }
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const data = await request<{ id: number; email: string }>('/auth/me')
  return { id: data.id, email: data.email }
}

export async function fetchProfile(): Promise<StudentProfile> {
  const data = await request<Record<string, unknown>>('/profile')
  return profileFromApi(data)
}

export async function saveProfile(
  profile: StudentProfile,
): Promise<StudentProfile> {
  const data = await request<Record<string, unknown>>('/profile', {
    method: 'PUT',
    body: JSON.stringify(profileToApi(profile)),
  })
  return profileFromApi(data)
}

export async function fetchApartments(): Promise<Apartment[]> {
  const data = await request<Record<string, unknown>[]>('/apartments')
  return data.map(apartmentFromApi)
}

export async function fetchApartment(id: number): Promise<Apartment> {
  const data = await request<Record<string, unknown>>(`/apartments/${id}`)
  return apartmentFromApi(data)
}

export async function createApartmentDraft(
  rawText: string,
  options?: {
    sourceUrl?: string
    photos?: string[]
    sourceSite?: string
  },
): Promise<Apartment> {
  const data = await request<Record<string, unknown>>('/apartments', {
    method: 'POST',
    body: JSON.stringify({
      raw_text: rawText,
      source_url: options?.sourceUrl,
      photos: options?.photos ?? [],
      source_site: options?.sourceSite,
      fetch_photos: true,
    }),
  })
  return apartmentFromApi(data)
}

export async function searchListings(): Promise<SearchListingsResponse> {
  const data = await request<Record<string, unknown>>('/search-listings', {
    method: 'POST',
    body: JSON.stringify({}),
  })
  const results = (data.results as Record<string, unknown>[]) ?? []
  return {
    results: results.map(searchResultFromApi),
    sourcesSearched: (data.sources_searched as string[]) ?? [],
    errors: (data.errors as Record<string, string>) ?? {},
    location: (data.location as string) ?? '',
    searchArea: (data.search_area as string) ?? '',
    maxRent: Number(data.max_rent ?? 0),
    campusGeocoded: Boolean(data.campus_geocoded),
    maxCommuteMinutes: Number(data.max_commute_minutes ?? 30),
    commuteMode: (data.commute_mode as SearchListingsResponse['commuteMode']) ?? 'walking',
    aiRanked: Boolean(data.ai_ranked),
  }
}

export async function fetchCommuteBatch(
  listings: { id: number; address: string }[],
): Promise<{
  results: Record<number, { minutes: number; distanceMiles: number }>
  campusGeocoded: boolean
  commuteMode: string
}> {
  const data = await request<Record<string, unknown>>('/commute/estimate-batch', {
    method: 'POST',
    body: JSON.stringify({
      listings: listings.map((item) => ({
        id: item.id,
        address: item.address,
      })),
    }),
  })
  const raw = (data.results as Record<string, { minutes: number; distance_miles: number }>) ?? {}
  const results: Record<number, { minutes: number; distanceMiles: number }> = {}
  for (const [id, estimate] of Object.entries(raw)) {
    results[Number(id)] = {
      minutes: estimate.minutes,
      distanceMiles: estimate.distance_miles,
    }
  }
  return {
    results,
    campusGeocoded: Boolean(data.campus_geocoded),
    commuteMode: String(data.commute_mode ?? 'walking'),
  }
}

export async function refreshListingPhotos(id: number): Promise<Apartment> {
  const data = await request<Record<string, unknown>>(
    `/apartments/${id}/refresh-photos`,
    { method: 'POST' },
  )
  return apartmentFromApi(data)
}

export async function parseListing(
  listingText: string,
  apartmentId?: number,
): Promise<Apartment> {
  const data = await request<Record<string, unknown>>('/parse-listing', {
    method: 'POST',
    body: JSON.stringify({
      listing_text: listingText,
      apartment_id: apartmentId,
    }),
  })
  return apartmentFromApi(data)
}

export async function updateApartmentListing(
  id: number,
  updates: {
    status?: Apartment['status']
    isFavorite?: boolean
    tourAt?: string | null
    tourNotes?: Apartment['tourNotes']
  },
): Promise<Apartment> {
  const body: Record<string, unknown> = {}
  if (updates.status !== undefined) body.status = updates.status
  if (updates.isFavorite !== undefined) body.is_favorite = updates.isFavorite
  if (updates.tourAt !== undefined) body.tour_at = updates.tourAt
  if (updates.tourNotes !== undefined) {
    body.tour_notes = updates.tourNotes.map((note) => ({
      id: note.id,
      text: note.text,
      created_at: note.createdAt,
    }))
  }

  const data = await request<Record<string, unknown>>(
    `/apartments/${id}/status`,
    {
      method: 'PUT',
      body: JSON.stringify(body),
    },
  )
  return apartmentFromApi(data)
}

export async function updateApartmentStatus(
  id: number,
  status: Apartment['status'],
): Promise<Apartment> {
  return updateApartmentListing(id, { status })
}

export async function deleteApartment(id: number): Promise<void> {
  const token = getAuthToken()
  const response = await fetch(`${API_BASE}/apartments/${id}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(parseErrorDetail(error, response.status))
  }
}

export interface AppConfig {
  aiMode: 'openai' | 'mock'
  mapboxConfigured: boolean
  mapboxToken: string | null
  mapboxStyleUrl: string
  database: string
  searchSources: string[]
}

export async function fetchAppConfig(): Promise<AppConfig> {
  const data = await request<Record<string, unknown>>('/config')
  return {
    aiMode: (data.ai_mode as 'openai' | 'mock') ?? 'mock',
    mapboxConfigured: Boolean(data.mapbox_configured),
    mapboxToken: (data.mapbox_token as string | null) ?? null,
    mapboxStyleUrl:
      (data.mapbox_style_url as string) ??
      'mapbox://styles/mapbox/streets-v12',
    database: (data.database as string) ?? 'disconnected',
    searchSources: (data.search_sources as string[]) ?? [],
  }
}

export interface ConfigValidation {
  openaiConfigured: boolean
  openaiWorking: boolean
  openaiError: string | null
  mapboxConfigured: boolean
  mapboxWorking: boolean
  mapboxError: string | null
  envFile: string
}

export async function validateAppConfig(): Promise<ConfigValidation> {
  const data = await request<Record<string, unknown>>('/config/validate')
  return {
    openaiConfigured: Boolean(data.openai_configured),
    openaiWorking: Boolean(data.openai_working),
    openaiError: (data.openai_error as string | null) ?? null,
    mapboxConfigured: Boolean(data.mapbox_configured),
    mapboxWorking: Boolean(data.mapbox_working),
    mapboxError: (data.mapbox_error as string | null) ?? null,
    envFile: (data.env_file as string) ?? '',
  }
}

export async function checkApiHealth(): Promise<{
  database: string
  ai: string
  mapbox?: string
}> {
  try {
    return await request<{ database: string; ai: string; mapbox?: string }>(
      '/health',
    )
  } catch {
    return { database: 'disconnected', ai: 'mock' }
  }
}
