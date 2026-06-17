import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useApartments } from '@/context/ApartmentsContext'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { fetchCommuteBatch } from '@/lib/api'
import { fetchMapboxCommuteBetweenAddresses } from '@/lib/geo'
import type { Apartment } from '@/types/apartment'
import { mapLocationForApartment } from '@/types/apartment'

export interface CommuteEstimate {
  minutes: number
  distanceMiles: number
}

interface CommuteContextValue {
  getCommute: (apartmentId: number) => CommuteEstimate | null
  isLoading: boolean
}

const CommuteContext = createContext<CommuteContextValue | null>(null)

function listingAddressForCommute(apartment: Apartment): string {
  return mapLocationForApartment(apartment)
}

export function CommuteProvider({ children }: { children: ReactNode }) {
  const { apartments } = useApartments()
  const { profile } = useStudentProfile()
  const [estimates, setEstimates] = useState<Record<number, CommuteEstimate>>(
    {},
  )
  const [isLoading, setIsLoading] = useState(false)

  const campusAddress =
    profile.campusLocation.trim() || profile.university.trim()

  useEffect(() => {
    const listings = apartments
      .map((apt) => ({
        id: apt.id,
        address: listingAddressForCommute(apt),
      }))
      .filter((item) => item.address.length >= 3)

    if (!campusAddress || listings.length === 0) {
      setEstimates({})
      return
    }

    let cancelled = false

    async function loadClientFallback(
      items: { id: number; address: string }[],
    ) {
      const fallback: Record<number, CommuteEstimate> = {}
      await Promise.all(
        items.map(async (item) => {
          const estimate = await fetchMapboxCommuteBetweenAddresses(
            campusAddress,
            item.address,
            profile.commuteMode,
          )
          if (estimate) {
            fallback[item.id] = estimate
          }
        }),
      )
      if (!cancelled) setEstimates(fallback)
    }

    async function load() {
      setIsLoading(true)
      try {
        const batch = await fetchCommuteBatch(listings)
        if (cancelled) return

        if (batch.campusGeocoded && Object.keys(batch.results).length > 0) {
          const fromServer = Object.fromEntries(
            Object.entries(batch.results).map(([id, estimate]) => [
              Number(id),
              {
                minutes: estimate.minutes,
                distanceMiles: estimate.distanceMiles,
              },
            ]),
          )
          setEstimates(fromServer)
          return
        }

        await loadClientFallback(listings)
      } catch {
        if (!cancelled) await loadClientFallback(listings)
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [apartments, campusAddress, profile.commuteMode])

  const getCommute = useCallback(
    (apartmentId: number) => estimates[apartmentId] ?? null,
    [estimates],
  )

  const value = useMemo(
    () => ({ getCommute, isLoading }),
    [getCommute, isLoading],
  )

  return (
    <CommuteContext.Provider value={value}>{children}</CommuteContext.Provider>
  )
}

export function useCommute(): CommuteContextValue {
  const context = useContext(CommuteContext)
  if (!context) {
    throw new Error('useCommute must be used within a CommuteProvider')
  }
  return context
}

export function useApartmentCommute(
  apartmentId: number,
): CommuteEstimate | null {
  const { getCommute } = useCommute()
  return getCommute(apartmentId)
}
