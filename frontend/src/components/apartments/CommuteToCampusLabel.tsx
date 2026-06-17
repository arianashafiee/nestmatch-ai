import { useApartmentCommute } from '@/context/CommuteContext'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { formatCommuteToCampus } from '@/lib/commute'
import { cn } from '@/lib/utils'
import type { Apartment } from '@/types/apartment'

interface CommuteToCampusLabelProps {
  apartment: Apartment
  className?: string
}

export function CommuteToCampusLabel({
  apartment,
  className,
}: CommuteToCampusLabelProps) {
  const { profile } = useStudentProfile()
  const estimate = useApartmentCommute(apartment.id)

  if (!estimate) return null

  const overLimit = estimate.minutes > profile.maxCommuteMinutes

  return (
    <p
      className={cn(
        'text-xs font-medium',
        overLimit ? 'text-amber-700' : 'text-emerald-700',
        className,
      )}
    >
      {formatCommuteToCampus(estimate.minutes, profile.commuteMode)}
    </p>
  )
}
