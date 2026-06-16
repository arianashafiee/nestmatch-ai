import type { Apartment, SearchListingsResponse } from '@/types/apartment'
import { apartmentFromApi, searchResultFromApi } from '@/types/apartment'
import {
  profileFromApi,
  profileToApi,
  type StudentProfile,
} from '@/types/studentProfile'

const API_BASE = '/api'

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
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(parseErrorDetail(error, response.status))
  }

  return response.json() as Promise<T>
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

export async function searchListings(
  profileId = 1,
): Promise<SearchListingsResponse> {
  const data = await request<Record<string, unknown>>('/search-listings', {
    method: 'POST',
    body: JSON.stringify({ profile_id: profileId }),
  })
  const results = (data.results as Record<string, unknown>[]) ?? []
  return {
    results: results.map(searchResultFromApi),
    sourcesSearched: (data.sources_searched as string[]) ?? [],
    errors: (data.errors as Record<string, string>) ?? {},
    location: (data.location as string) ?? '',
    maxRent: Number(data.max_rent ?? 0),
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
  profileId = 1,
  apartmentId?: number,
): Promise<Apartment> {
  const data = await request<Record<string, unknown>>('/parse-listing', {
    method: 'POST',
    body: JSON.stringify({
      listing_text: listingText,
      profile_id: profileId,
      apartment_id: apartmentId,
    }),
  })
  return apartmentFromApi(data)
}

export async function updateApartmentStatus(
  id: number,
  status: Apartment['status'],
): Promise<Apartment> {
  const data = await request<Record<string, unknown>>(
    `/apartments/${id}/status`,
    {
      method: 'PUT',
      body: JSON.stringify({ status }),
    },
  )
  return apartmentFromApi(data)
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
