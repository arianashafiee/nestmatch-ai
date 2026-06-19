import { estimateCommuteMinutes } from '@/lib/geo'
import type { CommuteMode } from '@/types/studentProfile'

export { estimateCommuteMinutes }

const MODE_SHORT_LABEL: Record<CommuteMode, string> = {
  walking: 'walk',
  transit: 'transit',
  biking: 'bike',
  driving: 'drive',
}

export function commuteModeShortLabel(mode: CommuteMode): string {
  return MODE_SHORT_LABEL[mode] ?? mode
}

export function formatCommuteToCampus(
  minutes: number,
  mode: CommuteMode,
): string {
  return `~${minutes} min ${commuteModeShortLabel(mode)} to campus`
}

/** Prefer API commute minutes; fall back to distance-based estimate. */
export function listingCommuteMinutes(
  listing: {
    commuteMinutes: number | null
    distanceMiles: number | null
  },
  mode: CommuteMode,
): number | null {
  if (listing.commuteMinutes != null) return listing.commuteMinutes
  if (listing.distanceMiles != null && listing.distanceMiles > 0) {
    return estimateCommuteMinutes(listing.distanceMiles, mode)
  }
  return null
}

export function listingWithinCommuteLimit(
  listing: {
    commuteMinutes: number | null
    distanceMiles: number | null
  },
  profile: { maxCommuteMinutes: number; commuteMode: CommuteMode },
): boolean {
  const minutes = listingCommuteMinutes(listing, profile.commuteMode)
  if (minutes == null) return false
  return minutes <= profile.maxCommuteMinutes
}

/** Prefer geocoded distance; fall back to precomputed minutes from search. */
export function commuteLabelFromDistance(
  distanceMiles: number | null | undefined,
  fallbackMinutes: number | null | undefined,
  mode: CommuteMode,
): string | null {
  if (distanceMiles != null && distanceMiles > 0) {
    return formatCommuteToCampus(
      estimateCommuteMinutes(distanceMiles, mode),
      mode,
    )
  }
  if (fallbackMinutes != null) {
    return formatCommuteToCampus(fallbackMinutes, mode)
  }
  return null
}
