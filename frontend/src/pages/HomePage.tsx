import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Kanban,
  Sparkles,
  UserCircle,
} from 'lucide-react'
import { ApartmentCard } from '@/components/apartments/ApartmentCard'
import { useApartments } from '@/context/ApartmentsContext'
import { useStudentProfile } from '@/context/StudentProfileContext'

export function HomePage() {
  const { profile, isProfileComplete } = useStudentProfile()
  const { apartments, parsingIds } = useApartments()

  const topMatches = [...apartments]
    .filter((a) => a.analysis)
    .sort((a, b) => (b.compatibilityScore ?? 0) - (a.compatibilityScore ?? 0))
    .slice(0, 3)

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-gradient-to-br from-indigo-50 to-white p-6 md:p-8">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-indigo-600 p-2.5 text-white">
            <Sparkles className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">
              Welcome to NestMatch AI
            </h2>
            <p className="mt-2 max-w-xl text-slate-600">
              NestMatch searches JHU Off-Campus Housing, Apartments.com, Zillow, Craigslist, and
              Realtor.com for your campus and budget — or paste any listing URL
              to pull photos and score it automatically.
            </p>
          </div>
        </div>
      </section>

      {parsingIds.length > 0 && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-800">
          AI is analyzing {parsingIds.length} listing
          {parsingIds.length === 1 ? '' : 's'}...
        </div>
      )}

      {topMatches.length > 0 && (
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-900">
              Your Top Matches
            </h3>
            <Link
              to="/board"
              className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
            >
              View all
            </Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {topMatches.map((apt) => (
              <ApartmentCard key={apt.id} apartment={apt} />
            ))}
          </div>
        </section>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          to="/profile"
          className="group rounded-xl border border-slate-200 p-5 transition-shadow hover:shadow-md"
        >
          <div className="flex items-center justify-between">
            <UserCircle className="h-8 w-8 text-indigo-600" />
            <ArrowRight className="h-4 w-4 text-slate-400 transition-transform group-hover:translate-x-1" />
          </div>
          <h3 className="mt-3 font-semibold text-slate-900">Student Profile</h3>
          <p className="mt-1 text-sm text-slate-500">
            {isProfileComplete
              ? `Budget: $${profile.maxRent}/mo · ${profile.maxCommuteMinutes} min ${profile.commuteMode}`
              : 'Set your budget, commute, and must-haves'}
          </p>
        </Link>

        <Link
          to="/board"
          className="group rounded-xl border border-slate-200 p-5 transition-shadow hover:shadow-md"
        >
          <div className="flex items-center justify-between">
            <Kanban className="h-8 w-8 text-indigo-600" />
            <ArrowRight className="h-4 w-4 text-slate-400 transition-transform group-hover:translate-x-1" />
          </div>
          <h3 className="mt-3 font-semibold text-slate-900">Hunting Board</h3>
          <p className="mt-1 text-sm text-slate-500">
            {apartments.length > 0
              ? `${apartments.length} listing${apartments.length === 1 ? '' : 's'} tracked`
              : 'Track apartments from Interested to Applied'}
          </p>
        </Link>
      </div>
    </div>
  )
}
