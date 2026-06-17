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
