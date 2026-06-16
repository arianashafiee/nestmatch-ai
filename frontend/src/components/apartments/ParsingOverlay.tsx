import { Loader2, Sparkles } from 'lucide-react'
import { ApartmentCardSkeleton } from '@/components/ui/Skeleton'

interface ParsingOverlayProps {
  count?: number
}

export function ParsingOverlay({ count = 1 }: ParsingOverlayProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3">
        <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
        <div>
          <p className="text-sm font-medium text-indigo-900">
            AI is analyzing {count === 1 ? 'your listing' : `${count} listings`}...
          </p>
          <p className="text-xs text-indigo-700">
            Extracting rent, scoring against your profile, and flagging red flags
          </p>
        </div>
        <Sparkles className="ml-auto h-5 w-5 text-indigo-400" />
      </div>
      {Array.from({ length: count }).map((_, i) => (
        <ApartmentCardSkeleton key={i} />
      ))}
    </div>
  )
}
