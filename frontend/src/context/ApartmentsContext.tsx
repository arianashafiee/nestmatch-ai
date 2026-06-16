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
  updateApartmentStatus,
} from '@/lib/api'
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
  syncApartment: (apartment: Apartment) => void
  refreshApartments: () => Promise<void>
  isAddModalOpen: boolean
  openAddModal: () => void
  closeAddModal: () => void
}

const ApartmentsContext = createContext<ApartmentsContextValue | null>(null)

const STORAGE_KEY = 'nestmatch-apartments'

function loadLocal(): Apartment[] {
  try {
    const stored =
      localStorage.getItem(STORAGE_KEY) ??
      localStorage.getItem('nestmatch-apartment-drafts')
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

function persistLocal(apartments: Apartment[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(apartments))
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
  const { showToast } = useToast()
  const [apartments, setApartments] = useState<Apartment[]>(loadLocal)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [parsingIds, setParsingIds] = useState<number[]>([])
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const parseQueue = useRef<Set<number>>(new Set())

  const refreshApartments = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await fetchApartments()
      setApartments(data)
      persistLocal(data)
    } catch {
      setApartments(loadLocal())
    } finally {
      setIsLoading(false)
    }
  }, [])

  const parseApartment = useCallback(
    async (id: number, rawText?: string): Promise<Apartment | null> => {
      if (parseQueue.current.has(id)) return null
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
        const parsed = await parseListing(text, 1, id)
        setApartments((prev) => {
          const next = upsertApartment(prev, parsed)
          persistLocal(next)
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
    [apartments, showToast],
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
      setIsSubmitting(true)
      setSubmitError(null)
      try {
        const draft = await createApartmentDraft(rawText.trim(), options)
        setApartments((prev) => {
          const next = [draft, ...prev]
          persistLocal(next)
          return next
        })
        const parsed = await parseApartment(draft.id, draft.rawText)
        return parsed ?? draft
      } catch (err) {
        const fallback: Apartment = {
          id: Date.now(),
          profileId: 1,
          rawText: rawText.trim(),
          sourceUrl: options?.sourceUrl ?? null,
          status: 'pending',
          title: null,
          compatibilityScore: null,
          analysis: null,
          photos: options?.photos ?? [],
          sourceSite: options?.sourceSite ?? null,
          landlordContact: null,
          parsedAt: null,
          createdAt: new Date().toISOString(),
        }
        setApartments((prev) => {
          const next = [fallback, ...prev]
          persistLocal(next)
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
    [parseApartment, showToast],
  )

  const syncApartment = useCallback((apartment: Apartment) => {
    setApartments((prev) => {
      const next = upsertApartment(prev, apartment)
      persistLocal(next)
      return next
    })
  }, [])

  const updateStatus = useCallback(
    async (id: number, status: ApartmentStatus) => {
      const previous = apartments.find((a) => a.id === id)
      if (!previous) return

      setApartments((prev) => {
        const next = prev.map((a) => (a.id === id ? { ...a, status } : a))
        persistLocal(next)
        return next
      })

      try {
        const updated = await updateApartmentStatus(id, status)
        setApartments((prev) => {
          const next = upsertApartment(prev, updated)
          persistLocal(next)
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
          persistLocal(next)
          return next
        })
        showToast(
          err instanceof Error ? err.message : 'Failed to update status',
          'error',
        )
      }
    },
    [apartments, showToast],
  )

  useEffect(() => {
    async function init() {
      setIsLoading(true)
      try {
        const data = await fetchApartments()
        setApartments(data)
        persistLocal(data)
        const pending = data.filter(
          (a) => a.status === 'pending' && !a.analysis,
        )
        for (const apt of pending) {
          await parseApartment(apt.id, apt.rawText)
        }
      } catch {
        const local = loadLocal()
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
  }, []) // eslint-disable-line react-hooks/exhaustive-deps -- run once on mount

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
