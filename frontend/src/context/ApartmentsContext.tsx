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
  fetchApartments,
  parseListing,
  updateApartmentListing,
  updateApartmentStatus,
} from '@/lib/api'
import { apartmentsStorageKey, useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import type { Apartment, ApartmentStatus } from '@/types/apartment'
import { normalizeApartment } from '@/types/apartment'

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
  toggleFavorite: (id: number, isFavorite: boolean) => Promise<void>
  syncApartment: (apartment: Apartment) => void
  refreshApartments: () => Promise<void>
  isAddModalOpen: boolean
  openAddModal: () => void
  closeAddModal: () => void
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
  const { showToast } = useToast()
  const [apartments, setApartments] = useState<Apartment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [parsingIds, setParsingIds] = useState<number[]>([])
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const parseQueue = useRef<Set<number>>(new Set())

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
        const updated = await updateApartmentListing(id, { isFavorite })
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

  const updateStatus = useCallback(
    async (id: number, status: ApartmentStatus) => {
      if (!user) return
      const previous = apartments.find((a) => a.id === id)
      if (!previous) return

      setApartments((prev) => {
        const next = prev.map((a) => (a.id === id ? { ...a, status } : a))
        persistLocal(user.id, next)
        return next
      })

      try {
        const updated = await updateApartmentStatus(id, status)
        setApartments((prev) => {
          const next = upsertApartment(prev, updated)
          persistLocal(user.id, next)
          return next
        })
        const label =
          status === 'archived'
            ? 'Archived'
            : status.replace('_', ' ')
        showToast(`Moved to ${label}`, 'success')
      } catch (err) {
        setApartments((prev) => {
          const next = upsertApartment(prev, previous)
          persistLocal(user.id, next)
          return next
        })
        showToast(
          err instanceof Error ? err.message : 'Failed to update status',
          'error',
        )
      }
    },
    [apartments, showToast, user],
  )

  useEffect(() => {
    if (!user) {
      setApartments([])
      setIsLoading(false)
      return
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
      toggleFavorite,
      syncApartment,
      refreshApartments,
      isAddModalOpen,
      openAddModal: () => setIsAddModalOpen(true),
      closeAddModal: () => {
        setIsAddModalOpen(false)
        setSubmitError(null)
      },
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
      toggleFavorite,
      syncApartment,
      refreshApartments,
      isAddModalOpen,
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
