import { MapPin, Navigation } from 'lucide-react'
import { useStudentProfile } from '@/context/StudentProfileContext'

interface MapPlaceholderProps {
  location: string
  commuteMinutes?: number | null
}

export function MapPlaceholder({ location, commuteMinutes }: MapPlaceholderProps) {
  const { profile } = useStudentProfile()
  const campus = profile.campusLocation || profile.university || 'Campus'

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="relative flex h-48 items-center justify-center bg-gradient-to-br from-slate-100 via-indigo-50 to-slate-100">
        <div className="absolute inset-0 opacity-30">
          <svg className="h-full w-full" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern
                id="grid"
                width="24"
                height="24"
                patternUnits="userSpaceOnUse"
              >
                <path
                  d="M24 0H0V24"
                  fill="none"
                  stroke="#cbd5e1"
                  strokeWidth="0.5"
                />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>
        </div>
        <div className="relative text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 text-white shadow-lg">
            <MapPin className="h-6 w-6" />
          </div>
          <p className="mt-3 text-sm font-medium text-slate-700">{location}</p>
          <p className="mt-1 text-xs text-slate-500">
            Add a Mapbox token in backend .env — see{' '}
            <a href="/settings" className="text-indigo-600 hover:underline">
              Settings
            </a>{' '}
            for setup steps
          </p>
        </div>
        <div className="absolute bottom-3 left-3 rounded-lg bg-white/90 px-3 py-1.5 text-xs shadow">
          <span className="font-medium text-slate-700">{campus}</span>
          <span className="text-slate-400"> · campus</span>
        </div>
      </div>
      {commuteMinutes != null && (
        <div className="flex items-center gap-2 border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
          <Navigation className="h-4 w-4 text-indigo-600" />
          Estimated {commuteMinutes} min {profile.commuteMode} to campus
        </div>
      )}
    </div>
  )
}
