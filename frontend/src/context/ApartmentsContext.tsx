import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  createApartmentDraft,
  deleteApartment as deleteApartmentApi,
  fetchApartments,
  parseListing,
  searchListings,
  updateApartmentListing as updateApartmentListingApi,
} from '@/lib/api'
import { apartmentsStorageKey, useAuth } from '@/context/AuthContext'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { useToast } from '@/context/ToastContext'
import {
  loadListingSearchCache,
  persistListingSearchCache,
  searchProfileFingerprint,
  type ListingSearchState,
} from '@/lib/listingSearchCache'
import { listingWithinCommuteLimit } from '@/lib/commute'
import { sortSearchResultsByScore } from '@/lib/listingActions'
import { filterListingsByBedroomRequirement } from '@/lib/profileRequirements'
import { listingWithinRentBudget } from '@/lib/rentSharing'
import type { Apartment, ApartmentStatus, SearchListingResult } from '@/types/apartment'
import { normalizeApartment } from '@/types/apartment'
import type { StudentProfile } from '@/types/studentProfile'

function filterSearchResultsForProfile(
  results: SearchListingResult[],
  profile: StudentProfile,
): SearchListingResult[] {
  return filterListingsByBedroomRequirement(results, profile).filter(
    (listing) =>
      listingWithinRentBudget(
        listing.rent,
        profile,
        `${listing.title} ${listing.snippet}`,
      ) && listingWithinCommuteLimit(listing, profile),
  )
}

interface ApartmentsContextValue {
  apartments: Apartment[]
  isLoading: boolean
  isSubmitting: boolean
  parsingIds: number[]
  submitError: string | null
  addApartment: (
    rawText: string,
    options?: {
      sourceUrl?: string
      photos?: string[]
      sourceSite?: string
    },
  ) => Promise<Apartment>
  parseApartment: (id: number, rawText?: string) => Promise<Apartment | null>
  updateStatus: (id: number, status: ApartmentStatus) => Promise<void>
  updateApartmentListing: (
    id: number,
    updates: {
      status?: ApartmentStatus
      isFavorite?: boolean
      tourAt?: string | null
      tourNotes?: Apartment['tourNotes']
    },
  ) => Promise<Apartment | null>
  toggleFavorite: (id: number, isFavorite: boolean) => Promise<void>
  deleteApartment: (id: number) => Promise<void>
  syncApartment: (apartment: Apartment) => void
  refreshApartments: () => Promise<void>
  isAddModalOpen: boolean
  openAddModal: () => void
  closeAddModal: () => void
  listingSearch: ListingSearchState | null
  isListingSearchInProgress: boolean
  isProfileStaleForSearch: boolean
  hasUnreadListingSearch: boolean
  searchListingsNearCampus: (options?: { force?: boolean }) => Promise<void>
  updateListingSearchResults: (results: SearchListingResult[]) => void
}

const ApartmentsContext = createContext<ApartmentsContextValue | null>(null)

function loadLocal(userId: number): Apartment[] {
  try {
    const stored = localStorage.getItem(apartmentsStorageKey(userId))
    if (stored) {
      const parsed = JSON.parse(stored) as Partial<Apartment>[]
      return parsed
        .filter((a) => a && typeof a.id === 'number')
        .map((a) => normalizeApartment(a as Partial<Apartment> & { id: number }))
    }
  } catch {
    // ignore
  }
  return []
}

function persistLocal(userId: number, apartments: Apartment[]) {
  localStorage.setItem(apartmentsStorageKey(userId), JSON.stringify(apartments))
}

function upsertApartment(list: Apartment[], updated: Apartment): Apartment[] {
  const normalized = normalizeApartment(updated)
  const idx = list.findIndex((a) => a.id === normalized.id)
  if (idx === -1) return [normalized, ...list]
  const next = [...list]
  next[idx] = normalized
  return next
}

export function ApartmentsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const { profile, isProfileComplete } = useStudentProfile()
  const { showToast } = useToast()
  const [apartments, setApartments] = useState<Apartment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [parsingIds, setParsingIds] = useState<number[]>([])
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [listingSearch, setListingSearch] = useState<ListingSearchState | null>(
    null,
  )
  const [isListingSearchInProgress, setIsListingSearchInProgress] =
    useState(false)
  const [hasUnreadListingSearch, setHasUnreadListingSearch] = useState(false)
  const parseQueue = useRef<Set<number>>(new Set())
  const isAddModalOpenRef = useRef(false)
  const listingSearchRequestId = useRef(0)

  const isProfileStaleForSearch = useMemo(() => {
    if (!listingSearch) return false
    return searchProfileFingerprint(profile) !== listingSearch.profileFingerprint
  }, [listingSearch, profile])

  const updateListingSearchResults = useCallback(
    (results: SearchListingResult[]) => {
      setListingSearch((prev) => {
        if (!prev) return prev
        const next = { ...prev, results }
        if (user) persistListingSearchCache(user.id, next)
        return next
      })
    },
    [user],
  )

  const searchListingsNearCampus = useCallback(
    async (options?: { force?: boolean }) => {
      if (!user || !isProfileComplete) return
      if (isListingSearchInProgress && !options?.force) return

      const requestId = listingSearchRequestId.current + 1
      listingSearchRequestId.current = requestId
      setIsListingSearchInProgress(true)

      try {
        const data = await searchListings()
        if (listingSearchRequestId.current !== requestId) return

        const fingerprint = searchProfileFingerprint(profile)
        const sortedResults = filterSearchResultsForProfile(
          sortSearchResultsByScore(data.results, apartments),
          profile,
        )
        const nextState: ListingSearchState = {
          results: sortedResults,
          sourcesSearched: data.sourcesSearched,
          searchErrors: data.errors,
          searchArea: data.searchArea,
          searchMeta: {
            campusGeocoded: data.campusGeocoded,
            maxCommuteMinutes: data.maxCommuteMinutes,
            commuteMode: data.commuteMode,
            aiRanked: data.aiRanked,
          },
          profileFingerprint: fingerprint,
          searchedAt: Date.now(),
        }

        setListingSearch(nextState)
        persistListingSearchCache(user.id, nextState)

        if (!isAddModalOpenRef.current) {
          setHasUnreadListingSearch(true)
        }

        if (data.results.length === 0) {
          const commuteBlocked = Object.values(data.errors).some((msg) =>
            msg.includes('No listings within'),
          )
          showToast(
            commuteBlocked
              ? 'No listings within your commute radius — try transit mode or increase max commute in Profile.'
              : data.errors.location
                ? data.errors.location
                : 'No listings found — sites may block automated search. Try pasting a direct link.',
            'info',
          )
        } else if (!isAddModalOpenRef.current) {
          showToast(
            data.aiRanked
              ? `Found ${data.results.length} listings — open Find Apartments to view`
              : `Found ${data.results.length} listings — open Find Apartments to view`,
            'success',
          )
        } else {
          showToast(
            data.aiRanked
              ? `Found ${data.results.length} listings — ranked by AI for your profile`
              : `Found ${data.results.length} listings across ${data.sourcesSearched.length} sites`,
            'success',
          )
        }
      } catch (err) {
        if (listingSearchRequestId.current !== requestId) return
        showToast(
          err instanceof Error ? err.message : 'Search failed',
          'error',
        )
      } finally {
        if (listingSearchRequestId.current === requestId) {
          setIsListingSearchInProgress(false)
        }
      }
    },
    [
      apartments,
      isListingSearchInProgress,
      isProfileComplete,
      profile,
      showToast,
      user,
    ],
  )

  const refreshApartments = useCallback(async () => {
    if (!user) return
    setIsLoading(true)
    try {
      const data = await fetchApartments()
      setApartments(data)
      persistLocal(user.id, data)
    } catch {
      setApartments(loadLocal(user.id))
    } finally {
      setIsLoading(false)
    }
  }, [user])

  const parseApartment = useCallback(
    async (id: number, rawText?: string): Promise<Apartment | null> => {
      if (!user || parseQueue.current.has(id)) return null
      parseQueue.current.add(id)
      setParsingIds((prev) => (prev.includes(id) ? prev : [...prev, id]))

      const apt = apartments.find((a) => a.id === id)
      const text = rawText ?? apt?.rawText
      if (!text) {
        parseQueue.current.delete(id)
        setParsingIds((prev) => prev.filter((x) => x !== id))
        return null
      }

      try {
        const parsed = await parseListing(text, id)
        setApartments((prev) => {
          const next = upsertApartment(prev, parsed)
          persistLocal(user.id, next)
          return next
        })
        showToast(
          `Scored "${parsed.title ?? 'listing'}" — ${parsed.compatibilityScore ?? parsed.analysis?.compatibility_score}/100`,
          'success',
          `/board/${parsed.id}`,
        )
        return parsed
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'AI parsing failed'
        showToast(message, 'error')
        return null
      } finally {
        parseQueue.current.delete(id)
        setParsingIds((prev) => prev.filter((x) => x !== id))
      }
    },
    [apartments, showToast, user],
  )

  const addApartment = useCallback(
    async (
      rawText: string,
      options?: {
        sourceUrl?: string
        photos?: string[]
        sourceSite?: string
      },
    ) => {
      if (!user) {
        throw new Error('Sign in to save listings')
      }
      setIsSubmitting(true)
      setSubmitError(null)
      try {
        const draft = await createApartmentDraft(rawText.trim(), options)
        setApartments((prev) => {
          const next = [draft, ...prev]
          persistLocal(user.id, next)
          return next
        })
        const parsed = await parseApartment(draft.id, draft.rawText)
        return parsed ?? draft
      } catch (err) {
        const fallback: Apartment = {
          id: Date.now(),
          profileId: 0,
          rawText: rawText.trim(),
          sourceUrl: options?.sourceUrl ?? null,
          status: 'pending',
          title: null,
          compatibilityScore: null,
          analysis: null,
          photos: options?.photos ?? [],
          sourceSite: options?.sourceSite ?? null,
          landlordContact: null,
          tourAt: null,
          tourNotes: [],
          isFavorite: false,
          parsedAt: null,
          createdAt: new Date().toISOString(),
          listingAddress: '',
        }
        setApartments((prev) => {
          const next = [fallback, ...prev]
          persistLocal(user.id, next)
          return next
        })
        setSubmitError(
          err instanceof Error
            ? `${err.message} — saved locally until the server is available.`
            : 'Saved locally until the server is available.',
        )
        showToast('Could not reach server — listing saved locally only.', 'error')
        return fallback
      } finally {
        setIsSubmitting(false)
      }
    },
    [parseApartment, showToast, user],
  )

  const syncApartment = useCallback(
    (apartment: Apartment) => {
      if (!user) return
      setApartments((prev) => {
        const next = upsertApartment(prev, apartment)
        persistLocal(user.id, next)
        return next
      })
    },
    [user],
  )

  const toggleFavorite = useCallback(
    async (id: number, isFavorite: boolean) => {
      if (!user) return
      const previous = apartments.find((a) => a.id === id)
      if (!previous) return

      setApartments((prev) => {
        const next = prev.map((a) =>
          a.id === id ? { ...a, isFavorite } : a,
        )
        persistLocal(user.id, next)
        return next
      })

      try {
        const updated = await updateApartmentListingApi(id, { isFavorite })
        setApartments((prev) => {
          const next = upsertApartment(prev, updated)
          persistLocal(user.id, next)
          return next
        })
      } catch (err) {
        setApartments((prev) => {
          const next = upsertApartment(prev, previous)
          persistLocal(user.id, next)
          return next
        })
        showToast(
          err instanceof Error ? err.message : 'Failed to update favorite',
          'error',
        )
      }
    },
    [apartments, showToast, user],
  )

  const deleteApartment = useCallback(
    async (id: number) => {
      if (!user) return
      const previous = apartments.find((a) => a.id === id)
      if (!previous) return

      setApartments((prev) => {
        const next = prev.filter((a) => a.id !== id)
        persistLocal(user.id, next)
        return next
      })

      try {
        await deleteApartmentApi(id)
        showToast('Listing removed from shortlist', 'success')
      } catch (err) {
        setApartments((prev) => {
          const next = upsertApartment(prev, previous)
          persistLocal(user.id, next)
          return next
        })
        showToast(
          err instanceof Error ? err.message : 'Failed to delete listing',
          'error',
        )
      }
    },
    [apartments, showToast, user],
  )

  const updateApartmentListingLocal = useCallback(
    async (
      id: number,
      updates: {
        status?: ApartmentStatus
        isFavorite?: boolean
        tourAt?: string | null
        tourNotes?: Apartment['tourNotes']
      },
    ): Promise<Apartment | null> => {
      if (!user) return null
      const previous = apartments.find((a) => a.id === id)
      if (!previous) return null

      const optimistic: Apartment = {
        ...previous,
        ...(updates.status !== undefined ? { status: updates.status } : {}),
        ...(updates.isFavorite !== undefined
          ? { isFavorite: updates.isFavorite }
          : {}),
        ...(updates.tourAt !== undefined ? { tourAt: updates.tourAt } : {}),
        ...(updates.tourNotes !== undefined
          ? { tourNotes: updates.tourNotes }
          : {}),
      }

      setApartments((prev) => {
        const next = upsertApartment(prev, optimistic)
        persistLocal(user.id, next)
        return next
      })

      try {
        const updated = await updateApartmentListingApi(id, updates)
        setApartments((prev) => {
          const next = upsertApartment(prev, updated)
          persistLocal(user.id, next)
          return next
        })
        if (updates.status === 'tour_scheduled' && updates.tourAt) {
          showToast('Tour scheduled', 'success')
        }
        return updated
      } catch (err) {
        setApartments((prev) => {
          const next = upsertApartment(prev, previous)
          persistLocal(user.id, next)
          return next
        })
        showToast(
          err instanceof Error ? err.message : 'Failed to update listing',
          'error',
        )
        return null
      }
    },
    [apartments, showToast, user],
  )

  const updateStatus = useCallback(
    async (id: number, status: ApartmentStatus) => {
      const previous = apartments.find((a) => a.id === id)
      if (status === 'tour_scheduled' && previous && !previous.tourAt) {
        showToast(
          'Set a tour date and time before moving to Tour Scheduled.',
          'error',
        )
        return
      }
      const updated = await updateApartmentListingLocal(id, { status })
      if (updated) {
        const label =
          status === 'archived' ? 'Archived' : status.replace('_', ' ')
        showToast(`Moved to ${label}`, 'success')
      }
    },
    [apartments, showToast, updateApartmentListingLocal],
  )

  useEffect(() => {
    isAddModalOpenRef.current = isAddModalOpen
    if (isAddModalOpen) {
      setHasUnreadListingSearch(false)
    }
  }, [isAddModalOpen])

  useEffect(() => {
    if (!user) {
      setApartments([])
      setListingSearch(null)
      setHasUnreadListingSearch(false)
      setIsLoading(false)
      return
    }

    const cachedSearch = loadListingSearchCache(user.id)
    if (cachedSearch) {
      const stale =
        searchProfileFingerprint(profile) !== cachedSearch.profileFingerprint
      setListingSearch(
        stale
          ? {
              ...cachedSearch,
              results: [],
              sourcesSearched: [],
              searchErrors: {},
              searchArea: '',
              searchMeta: null,
            }
          : {
              ...cachedSearch,
              results: filterSearchResultsForProfile(
                cachedSearch.results,
                profile,
              ),
            },
      )
    } else {
      setListingSearch(null)
    }

    const userId = user.id

    async function init() {
      setIsLoading(true)
      try {
        const data = await fetchApartments()
        setApartments(data)
        persistLocal(userId, data)
        const pending = data.filter(
          (a) => a.status === 'pending' && !a.analysis,
        )
        for (const apt of pending) {
          await parseApartment(apt.id, apt.rawText)
        }
      } catch {
        const local = loadLocal(userId)
        setApartments(local)
        for (const apt of local.filter(
          (a) => a.status === 'pending' && !a.analysis,
        )) {
          await parseApartment(apt.id, apt.rawText)
        }
      } finally {
        setIsLoading(false)
      }
    }
    init()
  }, [user?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!user) return

    setListingSearch((prev) => {
      if (!prev) return prev
      const currentFingerprint = searchProfileFingerprint(profile)
      if (currentFingerprint === prev.profileFingerprint) return prev
      if (
        prev.results.length === 0 &&
        prev.sourcesSearched.length === 0 &&
        !prev.searchArea
      ) {
        return prev
      }

      const cleared: ListingSearchState = {
        ...prev,
        results: [],
        sourcesSearched: [],
        searchErrors: {},
        searchArea: '',
        searchMeta: null,
      }
      persistListingSearchCache(user.id, cleared)
      return cleared
    })
  }, [
    profile.university,
    profile.campusLocation,
    profile.maxRent,
    profile.maxCommuteMinutes,
    profile.commuteMode,
    profile.livingSituation,
    profile.roommateCount,
    profile.mustHaves,
    profile.dealbreakers,
    profile.preferredLeaseLength,
    user,
  ])

  const value = useMemo(
    () => ({
      apartments,
      isLoading,
      isSubmitting,
      parsingIds,
      submitError,
      addApartment,
      parseApartment,
      updateStatus,
      updateApartmentListing: updateApartmentListingLocal,
      toggleFavorite,
      deleteApartment,
      syncApartment,
      refreshApartments,
      isAddModalOpen,
      openAddModal: () => setIsAddModalOpen(true),
      closeAddModal: () => {
        setIsAddModalOpen(false)
        setSubmitError(null)
      },
      listingSearch,
      isListingSearchInProgress,
      isProfileStaleForSearch,
      hasUnreadListingSearch,
      searchListingsNearCampus,
      updateListingSearchResults,
    }),
    [
      apartments,
      isLoading,
      isSubmitting,
      parsingIds,
      submitError,
      addApartment,
      parseApartment,
      updateStatus,
      updateApartmentListingLocal,
      toggleFavorite,
      deleteApartment,
      syncApartment,
      refreshApartments,
      isAddModalOpen,
      listingSearch,
      isListingSearchInProgress,
      isProfileStaleForSearch,
      hasUnreadListingSearch,
      searchListingsNearCampus,
      updateListingSearchResults,
    ],
  )

  return (
    <ApartmentsContext.Provider value={value}>
      {children}
    </ApartmentsContext.Provider>
  )
}

export function useApartments(): ApartmentsContextValue {
  const context = useContext(ApartmentsContext)
  if (!context) {
    throw new Error('useApartments must be used within an ApartmentsProvider')
  }
  return context
}
